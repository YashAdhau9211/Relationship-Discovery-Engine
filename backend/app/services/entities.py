from app.schemas.entities import EntityDetail, EntitySearchResponse, EntitySummary
from app.schemas.graph import GraphResponse


class EntityService:
    def __init__(self, repository) -> None:
        self.repository = repository

    def search_entities(self, query: str, limit: int = 25) -> EntitySearchResponse:
        results: list[EntitySummary] = [] if not query.strip() else self.repository.search(query=query, limit=limit)
        return EntitySearchResponse(query=query, count=len(results), results=results)

    def get_entity(self, entity_id: str) -> EntityDetail:
        return self.repository.get_by_id(entity_id)

    def get_ego_graph(self, entity_id: str, depth: int = 1) -> GraphResponse:
        return self.repository.get_ego_graph(entity_id=entity_id, depth=depth)
