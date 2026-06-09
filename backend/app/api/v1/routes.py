from fastapi import APIRouter

from app.api.v1 import entities, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(entities.router, prefix="/entities", tags=["entities"])
