from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from typing import Optional
from pydantic import BaseModel

from app.db import get_session
from app.services.user_service import get_or_create_user
from app.services.trip_service import (
    create_trip, list_trips, get_trip, soft_delete_trip, rate_trip
)

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
    return {
        "id": trip.id,
        "city": trip.city,
        "travel_date": trip.travel_date,
        "people_count": trip.people_count,
        "budget": trip.budget,
        "taste": trip.taste,
        "plan_markdown": trip.plan_markdown,
        "rating": trip.rating,
        "mode": trip.mode,
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