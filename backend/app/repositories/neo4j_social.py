from typing import Any

from app.core.errors import DomainError
from app.db.neo4j import Neo4jClient
from app.repositories.neo4j_entities import ENTITY_LABELS, display_name_expr, entity_id_expr
from app.schemas.entities import EntityDetail, EntitySummary
from app.schemas.social import SocialConnection


class Neo4jSocialRepository:
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

    def get_followers(self, entity_id: str, limit: int = 50) -> list[SocialConnection]:
        self.ensure_person(entity_id)
        cypher = self._connection_query("MATCH (other:Person)-[r:FOLLOWS]->(person:Person)", "incoming")
        return self._run_connection_query(cypher, entity_id=entity_id, limit=limit)

    def get_following(self, entity_id: str, limit: int = 50) -> list[SocialConnection]:
        self.ensure_person(entity_id)
        cypher = self._connection_query("MATCH (person:Person)-[r:FOLLOWS]->(other:Person)", "outgoing")
        return self._run_connection_query(cypher, entity_id=entity_id, limit=limit)

    def get_friends(self, entity_id: str, limit: int = 50) -> list[SocialConnection]:
        self.ensure_person(entity_id)
        cypher = self._connection_query("MATCH (person:Person)-[r:FRIENDS_WITH]-(other:Person)", "undirected")
        return self._run_connection_query(cypher, entity_id=entity_id, limit=limit)

    def get_mutual_followers(self, entity_id: str, limit: int = 50) -> list[SocialConnection]:
        self.ensure_person(entity_id)
        cypher = f"""
        MATCH (person:Person)
        WHERE {entity_id_expr("person")} = $entity_id
        MATCH (person)-[:FOLLOWS]->(other:Person)-[:FOLLOWS]->(person)
        RETURN labels(other)[0] AS label,
               {entity_id_expr("other")} AS id,
               {display_name_expr("other")} AS display_name,
               properties(other) AS properties,
               "FOLLOWS" AS relationship_type,
               "undirected" AS direction,
               null AS weight,
               null AS platform,
               null AS timestamp,
               {{mutual_follow: true}} AS relationship_properties
        ORDER BY display_name ASC
        LIMIT $limit
        """
        return self._run_connection_query(cypher, entity_id=entity_id, limit=limit)

    def social_counts(self, entity_id: str) -> dict[str, int]:
        self.ensure_person(entity_id)
        cypher = f"""
        MATCH (person:Person)
        WHERE {entity_id_expr("person")} = $entity_id
        OPTIONAL MATCH (incoming:Person)-[:FOLLOWS]->(person)
        WITH person, count(DISTINCT incoming) AS follower_count
        OPTIONAL MATCH (person)-[:FOLLOWS]->(outgoing:Person)
        WITH person, follower_count, count(DISTINCT outgoing) AS following_count
        OPTIONAL MATCH (person)-[:FRIENDS_WITH]-(friend:Person)
        WITH person, follower_count, following_count, count(DISTINCT friend) AS friend_count
        OPTIONAL MATCH (person)-[:FOLLOWS]->(mutual:Person)-[:FOLLOWS]->(person)
        RETURN follower_count,
               following_count,
               friend_count,
               count(DISTINCT mutual) AS mutual_count
        """
        with self.client.session() as session:
            record = session.run(cypher, entity_id=entity_id).single()
        return {
            "follower_count": record["follower_count"],
            "following_count": record["following_count"],
            "friend_count": record["friend_count"],
            "mutual_count": record["mutual_count"],
        }

    def get_shared_neighbors(self, source_id: str, target_id: str, limit: int = 50) -> list[SocialConnection]:
        self.ensure_person(source_id)
        self.ensure_person(target_id)
        cypher = f"""
        MATCH (source:Person), (target:Person)
        WHERE {entity_id_expr("source")} = $source_id
          AND {entity_id_expr("target")} = $target_id
        MATCH (source)-[:FOLLOWS|FRIENDS_WITH]-(mutual:Person)-[:FOLLOWS|FRIENDS_WITH]-(target)
        WHERE {entity_id_expr("mutual")} <> $source_id
          AND {entity_id_expr("mutual")} <> $target_id
        WITH DISTINCT mutual
        RETURN labels(mutual)[0] AS label,
               {entity_id_expr("mutual")} AS id,
               {display_name_expr("mutual")} AS display_name,
               properties(mutual) AS properties,
               "FOLLOWS" AS relationship_type,
               "undirected" AS direction,
               null AS weight,
               null AS platform,
               null AS timestamp,
               {{shared_neighbor: true}} AS relationship_properties
        ORDER BY display_name ASC
        LIMIT $limit
        """
        return self._run_connection_query(cypher, source_id=source_id, target_id=target_id, limit=limit)

    def platform_distribution(self, entity_id: str) -> dict[str, int]:
        self.ensure_person(entity_id)
        cypher = f"""
        MATCH (person:Person)-[r:FOLLOWS|FRIENDS_WITH]-(other:Person)
        WHERE {entity_id_expr("person")} = $entity_id
        RETURN coalesce(r.platform, "unknown") AS platform, count(r) AS count
        """
        with self.client.session() as session:
            records = session.run(cypher, entity_id=entity_id)
            return {record["platform"]: record["count"] for record in records}

    def _run_connection_query(self, cypher: str, **params: Any) -> list[SocialConnection]:
        with self.client.session() as session:
            records = session.run(cypher, **params)
            return [self._connection_from_record(record) for record in records]

    @staticmethod
    def _connection_query(match_clause: str, direction: str) -> str:
        return f"""
        {match_clause}
        WHERE {entity_id_expr("person")} = $entity_id
        RETURN labels(other)[0] AS label,
               {entity_id_expr("other")} AS id,
               {display_name_expr("other")} AS display_name,
               properties(other) AS properties,
               type(r) AS relationship_type,
               "{direction}" AS direction,
               r.weight AS weight,
               r.platform AS platform,
               r.timestamp AS timestamp,
               properties(r) AS relationship_properties
        ORDER BY coalesce(r.weight, 0.0) DESC, display_name ASC
        LIMIT $limit
        """

    @staticmethod
    def _connection_from_record(record: Any) -> SocialConnection:
        properties = dict(record["relationship_properties"] or {})
        return SocialConnection(
            entity=EntitySummary(
                id=record["id"],
                label=record["label"],
                display_name=record["display_name"],
                properties=dict(record["properties"] or {}),
            ),
            relationship_type=record["relationship_type"],
            direction=record["direction"],
            weight=record["weight"],
            platform=record["platform"],
            timestamp=record["timestamp"],
            properties=properties,
        )
