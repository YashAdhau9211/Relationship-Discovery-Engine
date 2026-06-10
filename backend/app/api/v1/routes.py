from fastapi import APIRouter

from app.api.v1 import connections, entities, health, social

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(entities.router, prefix="/entities", tags=["entities"])
api_router.include_router(social.router, prefix="/entities", tags=["social"])
api_router.include_router(connections.router, prefix="/entities", tags=["connections"])
