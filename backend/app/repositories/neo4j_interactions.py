from typing import Any

from app.core.errors import DomainError
from app.db.neo4j import Neo4jClient
from app.repositories.neo4j_entities import display_name_expr, entity_id_expr
from app.schemas.entities import EntityDetail


class Neo4jInteractionRepository:
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

    def direct_interaction_rows(self, source_id: str, target_id: str) -> list[dict[str, Any]]:
        self.ensure_person(source_id)
        self.ensure_person(target_id)
        cypher = f"""
        MATCH (source:Person), (target:Person)
        WHERE {entity_id_expr("source")} = $source_id
          AND {entity_id_expr("target")} = $target_id
        MATCH (source)-[interaction:INTERACTED_WITH]-(target)
        WITH interaction, startNode(interaction) AS source_node, endNode(interaction) AS target_node
        RETURN {entity_id_expr("source_node")} AS source_id,
               {entity_id_expr("target_node")} AS target_id,
               type(interaction) AS relationship_type,
               interaction.interaction_type AS interaction_type,
               coalesce(interaction.count, 1) AS count,
               interaction.platform AS platform,
               coalesce(interaction.recency_score, 0.0) AS recency_score,
               coalesce(interaction.timestamps, []) AS timestamps,
               properties(interaction) AS properties
        ORDER BY recency_score DESC, count DESC
        """
        with self.client.session() as session:
            return [dict(record) for record in session.run(cypher, source_id=source_id, target_id=target_id)]

    def shared_target_rows(self, source_id: str, target_id: str) -> list[dict[str, Any]]:
        self.ensure_person(source_id)
        self.ensure_person(target_id)
        cypher = f"""
        MATCH (source:Person), (target:Person)
        WHERE {entity_id_expr("source")} = $source_id
          AND {entity_id_expr("target")} = $target_id
        MATCH (source)-[source_rel:INTERACTED_WITH|CO_OCCURRED_IN]->(shared)<-[target_rel:INTERACTED_WITH|CO_OCCURRED_IN]-(target)
        WHERE NOT shared:Person OR {entity_id_expr("shared")} <> $source_id
        WITH source, target, shared,
             collect(DISTINCT source_rel) AS source_rels,
             collect(DISTINCT target_rel) AS target_rels
        MATCH (interactor:Person)-[:INTERACTED_WITH|CO_OCCURRED_IN]->(shared)
        WITH shared, source_rels, target_rels, count(DISTINCT interactor) AS total_interactors
        RETURN labels(shared)[0] AS target_label,
               {entity_id_expr("shared")} AS target_id,
               {display_name_expr("shared")} AS target_display_name,
               properties(shared) AS target_properties,
               reduce(total = 0, rel IN source_rels | total + coalesce(rel.count, 1)) AS source_interaction_count,
               reduce(total = 0, rel IN target_rels | total + coalesce(rel.count, 1)) AS target_interaction_count,
               total_interactors AS target_total_interactors,
               [value IN source_rels + target_rels | coalesce(value.interaction_type, value.event_type, type(value))] AS interaction_types,
               [value IN source_rels + target_rels | type(value)] AS relationship_types,
               [value IN source_rels + target_rels | coalesce(value.recency_score, 0.68)] AS recency_scores
        ORDER BY target_display_name ASC
        """
        with self.client.session() as session:
            return [dict(record) for record in session.run(cypher, source_id=source_id, target_id=target_id)]
