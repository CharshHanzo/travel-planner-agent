from fastapi import HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session
from typing import Optional

from app.db import get_session
from app.models.user import User
from app.utils.jwt import get_user_id_from_token

security = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id"),
    session: Session = Depends(get_session),
) -> Optional[User]:
    """获取当前登录用户（可选认证）"""
    if credentials:
        user_id = get_user_id_from_token(credentials.credentials)
        if user_id:
            user = session.get(User, user_id)
            if user and user.is_active:
                return user
    return None

async def require_user(
    user: Optional[User] = Depends(get_current_user),
) -> User:
    """要求必须登录"""
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    return user