from functools import lru_cache

from app.core.config import get_settings
from app.db.neo4j import Neo4jClient
from app.repositories.neo4j_entities import Neo4jEntityRepository
from app.repositories.neo4j_social import Neo4jSocialRepository
from app.services.entities import EntityService
from app.services.social import SocialService


@lru_cache
def get_neo4j_client() -> Neo4jClient:
    return Neo4jClient(get_settings())


def get_entity_service() -> EntityService:
    return EntityService(Neo4jEntityRepository(get_neo4j_client()))


def get_social_service() -> SocialService:
    return SocialService(Neo4jSocialRepository(get_neo4j_client()))
