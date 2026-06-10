from fastapi import APIRouter

from app.api.v1 import connections, education, entities, health, interactions, locations, organizations, social

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(entities.router, prefix="/entities", tags=["entities"])
api_router.include_router(social.router, prefix="/entities", tags=["social"])
api_router.include_router(connections.router, prefix="/entities", tags=["connections"])
api_router.include_router(organizations.router, prefix="/entities", tags=["organizations"])
api_router.include_router(education.router, prefix="/entities", tags=["education"])
api_router.include_router(locations.router, prefix="/entities", tags=["locations"])
api_router.include_router(interactions.router, prefix="/entities", tags=["interactions"])
