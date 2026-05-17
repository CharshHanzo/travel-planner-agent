from fastapi import APIRouter, Query, Depends
from sqlmodel import Session
from app.db import get_session
from app.services.user_service import get_or_create_user
from app.services.learning_engine import LearningEngine

router = APIRouter()

@router.get("/user/preferences")
def get_user_preferences(
    device_id: str = Query(...),
    session: Session = Depends(get_session),
):
    user = get_or_create_user(session, device_id)
    engine = LearningEngine(session)
    
    cached = engine.get_cached_preferences(user.id)
    if cached.get("sufficient"):
        return cached
    
    result = engine.update_user_preferences(user.id)
    return result
