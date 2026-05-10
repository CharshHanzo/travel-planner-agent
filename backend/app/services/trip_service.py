from sqlmodel import Session, select
from app.models.trip import Trip
from typing import Optional
import json

def get_trip_by_session(session: Session, session_id: str) -> Optional[Trip]:
    """根据 session_id 查找行程记录"""
    return session.exec(
        select(Trip).where(
            Trip.conversation_context.like(f'%"session_id": "{session_id}"%'),
            Trip.is_deleted == False,
        )
    ).first()

def upsert_trip(
    session: Session,
    user_id: str,
    session_id: str,
    city: Optional[str] = None,
    travel_date: Optional[str] = None,
    people_count: Optional[int] = None,
    budget: Optional[int] = None,
    taste: Optional[str] = None,
    plan_markdown: Optional[str] = None,
    weather_data: Optional[str] = None,
    activities_data: Optional[str] = None,
    food_data: Optional[str] = None,
    messages: Optional[list] = None,
    mode: str = "chat",
) -> Trip:
    """创建或更新对话模式下的行程记录"""
    import json
    
    trip = get_trip_by_session(session, session_id)
    
    if trip:
        # 更新已有记录
        if city is not None: trip.city = city or "未命名行程"
        if travel_date: trip.travel_date = travel_date
        if people_count: trip.people_count = people_count
        if budget: trip.budget = budget
        if taste: trip.taste = taste
        if plan_markdown: trip.plan_markdown = plan_markdown
        if weather_data: trip.weather_data = weather_data
        if activities_data: trip.activities_data = activities_data
        if food_data: trip.food_data = food_data
        
        # 更新会话上下文（保留原有数据）
        context = json.loads(trip.conversation_context or "{}")
        context["session_id"] = session_id
        if messages is not None:
            context["messages"] = messages
        trip.conversation_context = json.dumps(context, ensure_ascii=False)
        
        trip.semantic_text = generate_semantic_text(trip)
    else:
        # 创建新记录
        # 构建 conversation_context
        context = {"session_id": session_id}
        if messages:
            context["messages"] = messages
        
        trip = Trip(
            user_id=user_id,
            city=city or "未命名行程",
            travel_date=travel_date or "",
            people_count=people_count or 1,
            budget=budget or 0,
            taste=taste,
            plan_markdown=plan_markdown or "",
            weather_data=weather_data,
            activities_data=activities_data,
            food_data=food_data,
            conversation_context=json.dumps(context, ensure_ascii=False),
            mode=mode,
        )
        trip.semantic_text = generate_semantic_text(trip)
        session.add(trip)
    
    session.commit()
    session.refresh(trip)
    return trip

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