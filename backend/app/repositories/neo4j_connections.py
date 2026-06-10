import math
from typing import Any

from app.core.errors import DomainError
from app.db.neo4j import Neo4jClient
from app.repositories.neo4j_entities import display_name_expr, entity_id_expr
from app.schemas.common import Explanation
from app.schemas.connections import IntermediateNode, SecondDegreeConnectionResult, ThirdDegreeConnectionResult
from app.schemas.entities import EntityDetail, EntitySummary


class Neo4jConnectionRepository:
    KATZ_BETA = 0.005

    def __init__(self, client: Neo4jClient) -> None:
        self.client = client

    def ensure_person(self, entity_id: str) -> EntityDetail:
        cypher = f"""
        MATCH (n:Person)
        WHERE {entity_id_expr("n")} = $entity_id
        RETURN labels(n)[0] AS label,
               {entity_id_expr("n")} AS id,
               {display_name_expr("n")} AS display_name,
               properties(n) AS properties
        LIMIT 1
        """
        with self.client.session() as session:
            record = session.run(cypher, entity_id=entity_id).single()
        if record is None:
            raise DomainError(
                status_code=404,
                code="entity_not_found",
                message=f"Person '{entity_id}' was not found.",
                details={"entity_id": entity_id},
            )
        properties = dict(record["properties"] or {})
        return EntityDetail(
            id=record["id"],
            label=record["label"],
            display_name=record["display_name"],
            properties=properties,
            aliases=list(properties.get("aliases", [])) if isinstance(properties.get("aliases", []), list) else [],
            source_ids=list(properties.get("source_ids", [])) if isinstance(properties.get("source_ids", []), list) else [],
        )

    def discover_second_degree(self, entity_id: str, limit: int = 50) -> list[SecondDegreeConnectionResult]:
        source = self.ensure_person(entity_id)
        source_neighbor_ids = self._neighbor_ids(entity_id)
        if not source_neighbor_ids:
            return []

        candidates = self._candidate_rows(entity_id)
        shared_ids = sorted({neighbor["id"] for row in candidates for neighbor in row["shared_neighbors"]})
        shared_degrees = self._social_degrees(shared_ids)

        raw_results = []
        for row in candidates:
            candidate_neighbor_ids = set(row["candidate_neighbor_ids"])
            shared_neighbors = [self._summary_from_map(neighbor) for neighbor in row["shared_neighbors"]]
            shared_neighbor_count = len(shared_neighbors)
            union_size = len(source_neighbor_ids | candidate_neighbor_ids)
            jaccard = shared_neighbor_count / union_size if union_size else 0.0
            adamic_adar = sum(self._adamic_adar_component(shared_degrees.get(neighbor.id, 0)) for neighbor in shared_neighbors)
            paths = [[entity_id, neighbor.id, row["candidate_id"]] for neighbor in shared_neighbors]
            raw_results.append(
                {
                    "entity": EntitySummary(
                        id=row["candidate_id"],
                        label=row["candidate_label"],
                        display_name=row["candidate_display_name"],
                        properties=dict(row["candidate_properties"] or {}),
                    ),
                    "shared_neighbors": shared_neighbors,
                    "shared_neighbor_count": shared_neighbor_count,
                    "jaccard": jaccard,
                    "adamic_adar": adamic_adar,
                    "paths": paths,
                }
            )

        max_adamic_adar = max((result["adamic_adar"] for result in raw_results), default=0.0)
        results = []
        for result in raw_results:
            aa_normalized = result["adamic_adar"] / max_adamic_adar if max_adamic_adar else 0.0
            score = min(1.0, (0.55 * aa_normalized) + (0.30 * result["jaccard"]) + (0.15 * min(result["shared_neighbor_count"] / 5, 1.0)))
            candidate = result["entity"]
            shared_names = ", ".join(neighbor.display_name for neighbor in result["shared_neighbors"][:3])
            explanation = Explanation(
                summary=f"{source.display_name} is connected to {candidate.display_name} through {shared_names}.",
                algorithms=["bounded_bfs_depth_2", "jaccard_coefficient", "adamic_adar"],
                evidence=[
                    {
                        "type": "shared_social_neighbor",
                        "shared_neighbor_ids": [neighbor.id for neighbor in result["shared_neighbors"]],
                        "path_count": len(result["paths"]),
                    }
                ],
            )
            results.append(
                SecondDegreeConnectionResult(
                    entity=candidate,
                    score=round(score, 6),
                    shared_neighbor_count=result["shared_neighbor_count"],
                    jaccard=round(result["jaccard"], 6),
                    adamic_adar=round(result["adamic_adar"], 6),
                    shared_neighbors=result["shared_neighbors"],
                    paths=result["paths"],
                    explanation=explanation,
                )
            )

        return sorted(results, key=lambda item: (-item.score, -item.adamic_adar, item.entity.display_name))[:limit]

    def discover_third_degree(self, entity_id: str, limit: int = 50) -> list[ThirdDegreeConnectionResult]:
        source = self.ensure_person(entity_id)
        rows = self._third_degree_candidate_rows(entity_id)
        if not rows:
            return []

        intermediate_ids = sorted(
            {
                node["id"]
                for row in rows
                for path_nodes in row["intermediate_paths"]
                for node in path_nodes
            }
        )
        social_degrees = self._social_degrees(intermediate_ids)
        rank_by_id = {
            node_id: rank
            for rank, node_id in enumerate(
                sorted(intermediate_ids, key=lambda item: (-social_degrees.get(item, 0), item)),
                start=1,
            )
        }
        max_path_count = max((len(row["paths"]) for row in rows), default=1)
        max_intermediate_degree = max((social_degrees.get(node_id, 0) for node_id in intermediate_ids), default=1)

        results: list[ThirdDegreeConnectionResult] = []
        for row in rows:
            candidate = EntitySummary(
                id=row["candidate_id"],
                label=row["candidate_label"],
                display_name=row["candidate_display_name"],
                properties=dict(row["candidate_properties"] or {}),
            )
            path_count = len(row["paths"])
            katz_score = (self.KATZ_BETA**3) * path_count

            intermediate_nodes_by_id: dict[str, IntermediateNode] = {}
            for path_nodes in row["intermediate_paths"]:
                for node in path_nodes:
                    social_degree = social_degrees.get(node["id"], 0)
                    intermediate_nodes_by_id[node["id"]] = IntermediateNode(
                        id=node["id"],
                        label=node["label"],
                        display_name=node["display_name"],
                        centrality_rank=rank_by_id.get(node["id"], len(rank_by_id) + 1),
                        social_degree=social_degree,
                        properties=dict(node["properties"] or {}),
                    )

            average_intermediate_degree = (
                sum(node.social_degree for node in intermediate_nodes_by_id.values()) / len(intermediate_nodes_by_id)
                if intermediate_nodes_by_id
                else 0.0
            )
            path_component = path_count / max_path_count if max_path_count else 0.0
            centrality_component = average_intermediate_degree / max_intermediate_degree if max_intermediate_degree else 0.0
            score = min(1.0, (0.70 * path_component) + (0.30 * centrality_component))

            first_path = row["paths"][0] if row["paths"] else []
            bridge_names = [node.display_name for node in intermediate_nodes_by_id.values()]
            explanation = Explanation(
                summary=f"{source.display_name} is connected to {candidate.display_name} through {', '.join(bridge_names[:2])}.",
                algorithms=["bounded_bfs_depth_3", "katz_beta_0.005", "path_diversity", "intermediate_social_degree_rank"],
                evidence=[
                    {
                        "type": "third_degree_social_path",
                        "path_count": path_count,
                        "sample_path": first_path,
                        "intermediate_node_ids": list(intermediate_nodes_by_id.keys()),
                    }
                ],
            )
            results.append(
                ThirdDegreeConnectionResult(
                    entity=candidate,
                    score=round(score, 6),
                    path_count=path_count,
                    katz_score=katz_score,
                    paths=row["paths"],
                    intermediate_nodes=sorted(
                        intermediate_nodes_by_id.values(),
                        key=lambda node: (node.centrality_rank, node.display_name),
                    ),
                    explanation=explanation,
                )
            )

        return sorted(results, key=lambda item: (-item.score, -item.path_count, item.entity.display_name))[:limit]

    def _candidate_rows(self, entity_id: str) -> list[dict[str, Any]]:
        cypher = f"""
        MATCH (source:Person)
        WHERE {entity_id_expr("source")} = $entity_id
        MATCH (source)-[:FOLLOWS|FRIENDS_WITH]-(shared:Person)-[:FOLLOWS|FRIENDS_WITH]-(candidate:Person)
        WHERE {entity_id_expr("candidate")} <> $entity_id
          AND NOT (source)-[:FOLLOWS|FRIENDS_WITH]-(candidate)
        WITH DISTINCT candidate, shared
        WITH candidate, collect(DISTINCT shared) AS shared_neighbors
        MATCH (candidate)-[:FOLLOWS|FRIENDS_WITH]-(candidate_neighbor:Person)
        WITH candidate,
             shared_neighbors,
             collect(DISTINCT {entity_id_expr("candidate_neighbor")}) AS candidate_neighbor_ids
        RETURN labels(candidate)[0] AS candidate_label,
               {entity_id_expr("candidate")} AS candidate_id,
               {display_name_expr("candidate")} AS candidate_display_name,
               properties(candidate) AS candidate_properties,
               candidate_neighbor_ids AS candidate_neighbor_ids,
               [neighbor IN shared_neighbors | {{
                   label: labels(neighbor)[0],
                   id: {entity_id_expr("neighbor")},
                   display_name: {display_name_expr("neighbor")},
                   properties: properties(neighbor)
               }}] AS shared_neighbors
        """
        with self.client.session() as session:
            return [dict(record) for record in session.run(cypher, entity_id=entity_id)]

    def _third_degree_candidate_rows(self, entity_id: str) -> list[dict[str, Any]]:
        cypher = f"""
        MATCH (source:Person)
        WHERE {entity_id_expr("source")} = $entity_id
        MATCH (source)-[:FOLLOWS|FRIENDS_WITH]-(first:Person)-[:FOLLOWS|FRIENDS_WITH]-(second:Person)-[:FOLLOWS|FRIENDS_WITH]-(candidate:Person)
        WHERE {entity_id_expr("candidate")} <> $entity_id
          AND {entity_id_expr("first")} <> $entity_id
          AND {entity_id_expr("second")} <> $entity_id
          AND {entity_id_expr("first")} <> {entity_id_expr("second")}
          AND {entity_id_expr("first")} <> {entity_id_expr("candidate")}
          AND {entity_id_expr("second")} <> {entity_id_expr("candidate")}
          AND NOT (source)-[:FOLLOWS|FRIENDS_WITH]-(candidate)
          AND NOT (source)-[:FOLLOWS|FRIENDS_WITH]-(:Person)-[:FOLLOWS|FRIENDS_WITH]-(candidate)
        WITH DISTINCT candidate, first, second
        WITH candidate, collect(DISTINCT [first, second]) AS intermediate_paths
        RETURN labels(candidate)[0] AS candidate_label,
               {entity_id_expr("candidate")} AS candidate_id,
               {display_name_expr("candidate")} AS candidate_display_name,
               properties(candidate) AS candidate_properties,
               [pathNodes IN intermediate_paths |
                   [$node IN pathNodes | {{
                       label: labels($node)[0],
                       id: {entity_id_expr("$node")},
                       display_name: {display_name_expr("$node")},
                       properties: properties($node)
                   }}]
               ] AS intermediate_paths,
               [pathNodes IN intermediate_paths |
                   [$node IN pathNodes | {entity_id_expr("$node")}]
               ] AS intermediate_id_paths
        """
        cypher = cypher.replace("$node", "node")
        with self.client.session() as session:
            rows = []
            for record in session.run(cypher, entity_id=entity_id):
                row = dict(record)
                row["paths"] = [[entity_id, *path, row["candidate_id"]] for path in row["intermediate_id_paths"]]
                rows.append(row)
            return rows

    def _neighbor_ids(self, entity_id: str) -> set[str]:
        cypher = f"""
        MATCH (person:Person)-[:FOLLOWS|FRIENDS_WITH]-(neighbor:Person)
        WHERE {entity_id_expr("person")} = $entity_id
        RETURN collect(DISTINCT {entity_id_expr("neighbor")}) AS neighbor_ids
        """
        with self.client.session() as session:
            record = session.run(cypher, entity_id=entity_id).single()
        return set(record["neighbor_ids"] or [])

    def _social_degrees(self, entity_ids: list[str]) -> dict[str, int]:
        if not entity_ids:
            return {}
        cypher = f"""
        MATCH (person:Person)-[:FOLLOWS|FRIENDS_WITH]-(neighbor:Person)
        WHERE {entity_id_expr("person")} IN $entity_ids
        RETURN {entity_id_expr("person")} AS id,
               count(DISTINCT neighbor) AS degree
        """
        with self.client.session() as session:
            return {record["id"]: record["degree"] for record in session.run(cypher, entity_ids=entity_ids)}

    @staticmethod
    def _adamic_adar_component(degree: int) -> float:
        return 1 / math.log(degree) if degree > 1 else 0.0

    @staticmethod
    def _summary_from_map(row: dict[str, Any]) -> EntitySummary:
        return EntitySummary(
            id=row["id"],
            label=row["label"],
            display_name=row["display_name"],
            properties=dict(row["properties"] or {}),
        )
