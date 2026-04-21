from fastapi import APIRouter

from app.api.v1.endpoints import travel, health, agent

router = APIRouter()

router.include_router(health.router, prefix="/health", tags=["health"])
router.include_router(travel.router, prefix="/travel", tags=["travel"])
router.include_router(agent.router, prefix="/agent", tags=["agent"])