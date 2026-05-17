from fastapi import APIRouter

from app.api.v1.endpoints import travel, health, agent, chat, history, user

router = APIRouter()

router.include_router(health.router, prefix="/health", tags=["health"])
router.include_router(travel.router, prefix="/travel", tags=["travel"])
router.include_router(agent.router, prefix="/agent", tags=["agent"])
router.include_router(chat.router, prefix="/travel", tags=["travel"])
router.include_router(history.router, prefix="/travel", tags=["history"])
router.include_router(user.router, prefix="/travel", tags=["user"])