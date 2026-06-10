from typing import Any

from app.core.errors import DomainError
from app.db.neo4j import Neo4jClient
from app.repositories.neo4j_entities import display_name_expr, entity_id_expr
from app.schemas.entities import EntityDetail


class Neo4jLocationRepository:
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

    def shared_location_rows(self, source_id: str, target_id: str) -> list[dict[str, Any]]:
        self.ensure_person(source_id)
        self.ensure_person(target_id)
        cypher = f"""
        MATCH (source:Person)-[source_rel:LOCATED_AT]->(location:Location)<-[target_rel:LOCATED_AT]-(target:Person)
        WHERE {entity_id_expr("source")} = $source_id
          AND {entity_id_expr("target")} = $target_id
        RETURN labels(location)[0] AS location_label,
               {entity_id_expr("location")} AS location_id,
               {display_name_expr("location")} AS location_display_name,
               properties(location) AS location_properties,
               source_rel.location_type AS source_location_type,
               target_rel.location_type AS target_location_type,
               source_rel.start_ts AS source_start_ts,
               source_rel.end_ts AS source_end_ts,
               target_rel.start_ts AS target_start_ts,
               target_rel.end_ts AS target_end_ts,
               coalesce(source_rel.frequency, 0) AS source_frequency,
               coalesce(target_rel.frequency, 0) AS target_frequency,
               coalesce(source_rel.recency, 0.0) AS source_recency,
               coalesce(target_rel.recency, 0.0) AS target_recency,
               location.latitude AS latitude,
               location.longitude AS longitude
        ORDER BY location_display_name ASC
        """
        with self.client.session() as session:
            return [dict(record) for record in session.run(cypher, source_id=source_id, target_id=target_id)]
