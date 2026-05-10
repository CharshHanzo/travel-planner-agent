from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import Optional
from pydantic import BaseModel

from app.db import get_session
from app.models.trip import Trip
from app.services.user_service import get_or_create_user
from app.services.trip_service import (
    create_trip, list_trips, get_trip, soft_delete_trip, rate_trip
)
from app.utils.coordinates import extract_coordinates, format_coordinates_for_frontend, remove_coordinates_json

router = APIRouter()

class TripCreateRequest(BaseModel):
    device_id: str
    city: str
    travel_date: str
    people_count: int = 1
    budget: int = 0
    taste: Optional[str] = None
    departure: Optional[str] = None
    activity_count: int = 3
    plan_markdown: str
    weather_data: Optional[str] = None
    activities_data: Optional[str] = None
    food_data: Optional[str] = None
    conversation_context: Optional[str] = None
    mode: str = "quick"

class RatingRequest(BaseModel):
    rating: float

@router.post("/history/trips")
def save_trip(request: TripCreateRequest, session: Session = Depends(get_session)):
    user = get_or_create_user(session, request.device_id)
    trip = create_trip(
        session=session,
        user_id=user.id,
        city=request.city,
        travel_date=request.travel_date,
        people_count=request.people_count,
        budget=request.budget,
        taste=request.taste,
        departure=request.departure,
        activity_count=request.activity_count,
        plan_markdown=request.plan_markdown,
        weather_data=request.weather_data,
        activities_data=request.activities_data,
        food_data=request.food_data,
        conversation_context=request.conversation_context,
        mode=request.mode,
    )
    return {"id": trip.id, "created_at": trip.created_at.isoformat()}

@router.get("/history/trips")
def get_trips(
    device_id: str = Query(...),
    city: Optional[str] = Query(None),
    rating_min: Optional[float] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    session: Session = Depends(get_session),
):
    user = get_or_create_user(session, device_id)
    trips = list_trips(
        session, user.id, city=city, rating_min=rating_min,
        offset=offset, limit=limit
    )
    return {
        "trips": [
            {
                "id": t.id,
                "city": t.city,
                "travel_date": t.travel_date,
                "people_count": t.people_count,
                "budget": t.budget,
                "taste": t.taste,
                "rating": t.rating,
                "mode": t.mode,
                "created_at": t.created_at.isoformat(),
            }
            for t in trips
        ],
        "total": len(trips),
    }

@router.get("/history/trips/{trip_id}")
def get_trip_detail(trip_id: str, session: Session = Depends(get_session)):
    trip = get_trip(session, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="行程不存在")
    
    import json
    messages = []
    session_id = ""
    if trip.conversation_context:
        try:
            ctx = json.loads(trip.conversation_context)
            raw_messages = ctx.get("messages", [])
            session_id = ctx.get("session_id", "")
            
            # 清洗每条 AI 消息
            for msg in raw_messages:
                if msg.get("role") == "assistant":
                    content = msg.get("content", "")
                    coords = extract_coordinates(content)
                    messages.append({
                        "role": msg.get("role"),
                        "content": remove_coordinates_json(content),
                        "coordinates": format_coordinates_for_frontend(coords) if coords else None,
                        "agent_calls": msg.get("agent_calls", []),
                        "timestamp": msg.get("timestamp", 0),
                    })
                else:
                    messages.append(msg)
        except:
            pass
    
    return {
        "id": trip.id,
        "city": trip.city,
        "travel_date": trip.travel_date,
        "people_count": trip.people_count,
        "budget": trip.budget,
        "taste": trip.taste,
        "plan_markdown": remove_coordinates_json(trip.plan_markdown or ""),
        "rating": trip.rating,
        "mode": trip.mode,
        "session_id": session_id,
        "messages": messages,
        "created_at": trip.created_at.isoformat(),
    }

@router.delete("/history/trips/{trip_id}")
def delete_trip(trip_id: str, session: Session = Depends(get_session)):
    success = soft_delete_trip(session, trip_id)
    if not success:
        raise HTTPException(status_code=404, detail="行程不存在")
    return {"message": "删除成功"}

@router.post("/history/trips/{trip_id}/rate")
def rate_trip_endpoint(
    trip_id: str,
    request: RatingRequest,
    session: Session = Depends(get_session),
):
    trip = rate_trip(session, trip_id, request.rating)
    if not trip:
        raise HTTPException(status_code=404, detail="行程不存在")
    return {"message": "评分成功", "rating": trip.rating}

@router.get("/history/sessions/{identifier}")
def get_session_context(identifier: str, session: Session = Depends(get_session)):
    """支持 session_id 或 trip_id 获取对话上下文，用于恢复对话"""
    import json
    
    # 先按 session_id 查
    trip = session.exec(
        select(Trip).where(
            Trip.conversation_context.like(f'%"session_id": "{identifier}"%'),
            Trip.is_deleted == False,
        )
    ).first()
    
    # 如果没找到，按 trip_id 查
    if not trip:
        trip = session.exec(
            select(Trip).where(
                Trip.id == identifier,
                Trip.is_deleted == False,
            )
        ).first()
    
    if not trip:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    # 解析 session_id
    session_id = ""
    context_data = {}
    messages = []
    try:
        context_data = json.loads(trip.conversation_context or "{}")
        messages = context_data.get("messages", [])
        session_id = context_data.get("session_id", "")
    except:
        pass
    
    # 处理消息列表：提取坐标并移除 JSON 块
    cleaned_messages = []
    for msg in messages:
        if msg.get("role") == "assistant":
            content = msg.get("content", "")
            # 提取并移除坐标
            coords = extract_coordinates(content)
            clean_content = remove_coordinates_json(content)
            cleaned_messages.append({
                "role": msg.get("role"),
                "content": clean_content,
                "coordinates": format_coordinates_for_frontend(coords) if coords else None,
                "agent_calls": msg.get("agent_calls", []),
                "timestamp": msg.get("timestamp", 0),
            })
        else:
            cleaned_messages.append(msg)
    
    return {
        "session_id": session_id or identifier,
        "city": trip.city,
        "travel_date": trip.travel_date,
        "people_count": trip.people_count,
        "budget": trip.budget,
        "taste": trip.taste,
        "messages": cleaned_messages,
        "preferences": {
            "budget": trip.budget,
            "taste": trip.taste,
            "date": trip.travel_date,
            "people": trip.people_count,
        }
    }