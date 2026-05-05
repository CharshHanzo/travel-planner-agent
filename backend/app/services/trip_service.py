from sqlmodel import Session, select
from app.models.trip import Trip
from typing import Optional

def create_trip(session: Session, **kwargs) -> Trip:
    trip = Trip(**kwargs)
    trip.semantic_text = generate_semantic_text(trip)
    session.add(trip)
    session.commit()
    session.refresh(trip)
    return trip

def get_trip(session: Session, trip_id: str) -> Optional[Trip]:
    return session.exec(
        select(Trip).where(Trip.id == trip_id, Trip.is_deleted == False)
    ).first()

def list_trips(
    session: Session,
    user_id: str,
    city: Optional[str] = None,
    rating_min: Optional[float] = None,
    offset: int = 0,
    limit: int = 10,
) -> list[Trip]:
    query = select(Trip).where(
        Trip.user_id == user_id,
        Trip.is_deleted == False,
    )
    
    if city:
        query = query.where(Trip.city.contains(city))
    if rating_min is not None:
        query = query.where(Trip.rating >= rating_min)
    
    query = query.order_by(Trip.created_at.desc()).offset(offset).limit(limit)
    return session.exec(query).all()

def soft_delete_trip(session: Session, trip_id: str) -> bool:
    trip = session.get(Trip, trip_id)
    if trip:
        trip.is_deleted = True
        session.commit()
        return True
    return False

def rate_trip(session: Session, trip_id: str, rating: float) -> Optional[Trip]:
    trip = session.get(Trip, trip_id)
    if trip:
        trip.rating = rating
        session.commit()
        session.refresh(trip)
    return trip

def generate_semantic_text(trip: Trip) -> str:
    parts = [
        f"{trip.people_count}人",
        f"{trip.budget}元预算",
        f"去{trip.city}旅行",
    ]
    if trip.taste and trip.taste != "不挑":
        parts.append(f"吃{trip.taste}口味")
    return " ".join(parts)