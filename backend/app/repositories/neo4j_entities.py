from typing import Any

from app.core.errors import DomainError
from app.db.neo4j import Neo4jClient
from app.schemas.entities import EntityDetail, EntitySummary
from app.schemas.graph import GraphEdge, GraphNode, GraphResponse, GraphStatistics

ENTITY_LABELS = [
    "Person",
    "Organization",
    "EducationInstitution",
    "Location",
    "Event",
    "Community",
]


def entity_id_expr(alias: str = "n") -> str:
    return (
        "CASE "
        f"WHEN {alias}:Person THEN {alias}.canonical_id "
        f"WHEN {alias}:Organization THEN {alias}.canonical_id "
        f"WHEN {alias}:EducationInstitution THEN {alias}.institution_id "
        f"WHEN {alias}:Location THEN {alias}.location_id "
        f"WHEN {alias}:Event THEN {alias}.event_id "
        f"WHEN {alias}:Community THEN {alias}.community_id "
        f"ELSE coalesce({alias}.canonical_id, {alias}.institution_id, {alias}.location_id, {alias}.event_id, {alias}.community_id) "
        "END"
    )


def display_name_expr(alias: str = "n") -> str:
    return (
        f"coalesce({alias}.name, {alias}.org_name, {alias}.location_name, "
        f"{alias}.event_id, {alias}.community_id, {entity_id_expr(alias)})"
    )


class Neo4jEntityRepository:
    def __init__(self, client: Neo4jClient) -> None:
        self.client = client

    def search(self, query: str, limit: int = 25) -> list[EntitySummary]:
        normalized = query.strip().lower()
        cypher = f"""
        MATCH (n)
        WHERE any(label IN labels(n) WHERE label IN $labels)
          AND (
            toLower(coalesce(n.name, '')) CONTAINS $query_text OR
            toLower(coalesce(n.org_name, '')) CONTAINS $query_text OR
            toLower(coalesce(n.location_name, '')) CONTAINS $query_text OR
            toLower(coalesce(n.canonical_id, '')) CONTAINS $query_text OR
            toLower(coalesce(n.institution_id, '')) CONTAINS $query_text OR
            toLower(coalesce(n.location_id, '')) CONTAINS $query_text OR
            toLower(coalesce(n.event_id, '')) CONTAINS $query_text OR
            toLower(coalesce(n.community_id, '')) CONTAINS $query_text
          )
        RETURN labels(n)[0] AS label,
               {entity_id_expr("n")} AS id,
               {display_name_expr("n")} AS display_name,
               properties(n) AS properties
        ORDER BY display_name ASC
        LIMIT $limit
        """
        with self.client.session() as session:
            records = session.run(cypher, labels=ENTITY_LABELS, query_text=normalized, limit=limit)
            return [self._summary_from_record(record) for record in records]

    def get_by_id(self, entity_id: str) -> EntityDetail:
        cypher = f"""
        MATCH (n)
        WHERE any(label IN labels(n) WHERE label IN $labels)
          AND {entity_id_expr("n")} = $entity_id
        RETURN labels(n)[0] AS label,
               {entity_id_expr("n")} AS id,
               {display_name_expr("n")} AS display_name,
               properties(n) AS properties
        LIMIT 1
        """
        with self.client.session() as session:
            record = session.run(cypher, labels=ENTITY_LABELS, entity_id=entity_id).single()
            if record is None:
                raise DomainError(
                    status_code=404,
                    code="entity_not_found",
                    message=f"Entity '{entity_id}' was not found.",
                    details={"entity_id": entity_id},
                )
            summary = self._summary_from_record(record)
            return EntityDetail(
                **summary.model_dump(),
                aliases=list(summary.properties.get("aliases", [])),
                source_ids=list(summary.properties.get("source_ids", [])),
            )

    def get_ego_graph(self, entity_id: str, depth: int = 1) -> GraphResponse:
        if depth != 1:
            raise DomainError(
                status_code=400,
                code="unsupported_graph_depth",
                message="Feature 1 supports depth=1 only.",
                details={"requested_depth": depth, "supported_depth": 1},
            )

        center = self.get_by_id(entity_id)
        cypher = f"""
        MATCH (center)
        WHERE any(label IN labels(center) WHERE label IN $labels)
          AND {entity_id_expr("center")} = $entity_id
        MATCH (center)-[r]-(neighbor)
        WHERE any(label IN labels(neighbor) WHERE label IN $labels)
        WITH r, neighbor, startNode(r) AS source_node, endNode(r) AS target_node
        RETURN labels(neighbor)[0] AS neighbor_label,
               {entity_id_expr("neighbor")} AS neighbor_id,
               {display_name_expr("neighbor")} AS neighbor_display_name,
               properties(neighbor) AS neighbor_properties,
               elementId(r) AS edge_id,
               {entity_id_expr("source_node")} AS source_id,
               {entity_id_expr("target_node")} AS target_id,
               type(r) AS edge_type,
               properties(r) AS edge_properties
        """
        with self.client.session() as session:
            records = list(session.run(cypher, labels=ENTITY_LABELS, entity_id=entity_id))

        center = GraphNode(
            id=center.id,
            label=center.label,
            display_name=center.display_name,
            properties=center.properties,
        )
        neighbors = [
            GraphNode(
                id=record["neighbor_id"],
                label=record["neighbor_label"],
                display_name=record["neighbor_display_name"],
                properties=dict(record["neighbor_properties"] or {}),
            )
            for record in records
        ]
        edges = [
            GraphEdge(
                id=record["edge_id"],
                source=record["source_id"],
                target=record["target_id"],
                type=record["edge_type"],
                directed=record["edge_type"] != "FRIENDS_WITH",
                properties=dict(record["edge_properties"] or {}),
            )
            for record in records
        ]
        nodes_by_id = {center.id: center, **{node.id: node for node in neighbors}}
        return GraphResponse(
            center_id=center.id,
            depth=depth,
            nodes=list(nodes_by_id.values()),
            edges=edges,
            statistics=GraphStatistics(node_count=len(nodes_by_id), edge_count=len(edges), depth=depth),
        )

    @staticmethod
    def _summary_from_record(record: Any) -> EntitySummary:
        return EntitySummary(
            id=record["id"],
            label=record["label"],
            display_name=record["display_name"],
            properties=dict(record["properties"] or {}),
        )
