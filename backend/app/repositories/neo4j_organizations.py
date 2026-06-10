from typing import Any

from app.core.errors import DomainError
from app.db.neo4j import Neo4jClient
from app.repositories.neo4j_entities import display_name_expr, entity_id_expr
from app.schemas.entities import EntityDetail


class Neo4jOrganizationRepository:
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

    def shared_organization_rows(self, source_id: str, target_id: str) -> list[dict[str, Any]]:
        self.ensure_person(source_id)
        self.ensure_person(target_id)
        cypher = f"""
        MATCH (source:Person)-[source_rel:WORKS_AT|MEMBER_OF]->(org:Organization)<-[target_rel:WORKS_AT|MEMBER_OF]-(target:Person)
        WHERE {entity_id_expr("source")} = $source_id
          AND {entity_id_expr("target")} = $target_id
        RETURN labels(org)[0] AS org_label,
               {entity_id_expr("org")} AS org_id,
               {display_name_expr("org")} AS org_display_name,
               properties(org) AS org_properties,
               type(source_rel) AS source_relationship_type,
               type(target_rel) AS target_relationship_type,
               source_rel.role AS source_role,
               target_rel.role AS target_role,
               source_rel.start_date AS source_start_date,
               source_rel.end_date AS source_end_date,
               target_rel.start_date AS target_start_date,
               target_rel.end_date AS target_end_date,
               coalesce(org.pagerank_score, 0.0) AS org_importance_score
        ORDER BY org_importance_score DESC, org_display_name ASC
        """
        with self.client.session() as session:
            return [dict(record) for record in session.run(cypher, source_id=source_id, target_id=target_id)]
