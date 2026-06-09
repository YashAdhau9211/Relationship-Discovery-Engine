from app.core.config import Settings
from app.db.neo4j import Neo4jClient


NODE_CONSTRAINTS = [
    "CREATE CONSTRAINT person_canonical_id IF NOT EXISTS FOR (n:Person) REQUIRE n.canonical_id IS UNIQUE",
    "CREATE CONSTRAINT organization_canonical_id IF NOT EXISTS FOR (n:Organization) REQUIRE n.canonical_id IS UNIQUE",
    "CREATE CONSTRAINT education_institution_id IF NOT EXISTS FOR (n:EducationInstitution) REQUIRE n.institution_id IS UNIQUE",
    "CREATE CONSTRAINT location_id IF NOT EXISTS FOR (n:Location) REQUIRE n.location_id IS UNIQUE",
    "CREATE CONSTRAINT event_id IF NOT EXISTS FOR (n:Event) REQUIRE n.event_id IS UNIQUE",
    "CREATE CONSTRAINT community_id IF NOT EXISTS FOR (n:Community) REQUIRE n.community_id IS UNIQUE",
]

NODE_INDEXES = [
    "CREATE TEXT INDEX person_name_text IF NOT EXISTS FOR (n:Person) ON (n.name)",
    "CREATE TEXT INDEX organization_name_text IF NOT EXISTS FOR (n:Organization) ON (n.org_name)",
    "CREATE TEXT INDEX education_name_text IF NOT EXISTS FOR (n:EducationInstitution) ON (n.name)",
]


def bootstrap_schema(settings: Settings) -> None:
    client = Neo4jClient(settings)
    try:
        with client.session() as session:
            for statement in [*NODE_CONSTRAINTS, *NODE_INDEXES]:
                session.run(statement).consume()
    finally:
        client.close()
