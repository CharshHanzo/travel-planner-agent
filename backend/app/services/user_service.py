from sqlmodel import Session, select
from app.models.user import User

def get_or_create_user(session: Session, device_id: str) -> User:
    user = session.exec(
        select(User).where(User.device_id == device_id)
    ).first()
    
    if not user:
        user = User(device_id=device_id, nickname=f"旅行者_{device_id[:8]}")
        session.add(user)
        session.commit()
        session.refresh(user)
    
    return user

def update_nickname(session: Session, user_id: str, nickname: str) -> User:
    user = session.get(User, user_id)
    if user:
        user.nickname = nickname
        session.commit()
        session.refresh(user)
    return user