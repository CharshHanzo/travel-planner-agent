from fastapi import APIRouter, HTTPException, Depends, Query
from sqlmodel import Session, select
from datetime import datetime

from app.db import get_session
from app.schemas.auth import (
    RegisterRequest, LoginRequest, AuthResponse
)
from app.models.user import User
from app.models.user_device import UserDevice
from app.models.session import Session as SessionModel
from app.models.trip import Trip
from app.core.dependencies import require_user
from app.utils.password import hash_password, verify_password
from app.utils.jwt import (
    create_access_token, create_refresh_token, decode_token, get_user_id_from_token
)

router = APIRouter(prefix="/auth", tags=["认证"])

@router.post("/register")
async def register(request: RegisterRequest, session: Session = Depends(get_session)):
    """用户注册"""
    # 1. 检查邮箱唯一性
    existing = session.exec(select(User).where(User.email == request.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="邮箱已被注册")
    
    # 2. 创建用户
    username = request.username or request.email.split("@")[0]
    password_hash = hash_password(request.password)
    
    user = User(
        email=request.email,
        username=username,
        password_hash=password_hash,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    
    # 3. 绑定设备
    if request.device_id:
        device = UserDevice(
            user_id=user.id,
            device_id=request.device_id,
            last_used_at=datetime.utcnow(),
        )
        session.add(device)
        
        # 4. 合并匿名 trips
        _merge_anonymous_trips(session, user.id, request.device_id)
        session.commit()
    
    # 5. 生成 Token
    access_token = create_access_token(user.id, user.email)
    refresh_token, expires_at = create_refresh_token(user.id, user.email)
    
    # 6. 存储 refresh_token
    session_model = SessionModel(
        user_id=user.id,
        refresh_token=refresh_token,
        expires_at=expires_at,
    )
    session.add(session_model)
    session.commit()
    
    return {
        "code": 200,
        "message": "注册成功",
        "data": {
            "user": {"id": user.id, "email": user.email, "username": user.username},
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": 3600,
        }
    }

@router.post("/login")
async def login(request: LoginRequest, session: Session = Depends(get_session)):
    """用户登录"""
    # 1. 查找用户
    user = session.exec(select(User).where(User.email == request.email)).first()
    if not user:
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    
    # 2. 验证密码
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    
    # 3. 更新设备绑定
    if request.device_id:
        existing_device = session.exec(
            select(UserDevice).where(UserDevice.device_id == request.device_id)
        ).first()
        if existing_device:
            existing_device.last_used_at = datetime.utcnow()
            existing_device.user_id = user.id
        else:
            device = UserDevice(
                user_id=user.id,
                device_id=request.device_id,
                last_used_at=datetime.utcnow(),
            )
            session.add(device)
        
        # 4. 合并匿名 trips
        _merge_anonymous_trips(session, user.id, request.device_id)
        session.commit()
    
    # 5. 生成 Token
    access_token = create_access_token(user.id, user.email)
    refresh_token, expires_at = create_refresh_token(user.id, user.email, request.remember_me)
    
    # 6. 存储 refresh_token
    session_model = SessionModel(
        user_id=user.id,
        refresh_token=refresh_token,
        expires_at=expires_at,
    )
    session.add(session_model)
    session.commit()
    
    return {
        "code": 200,
        "message": "登录成功",
        "data": {
            "user": {"id": user.id, "email": user.email, "username": user.username},
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": 3600,
        }
    }

@router.post("/refresh")
async def refresh_token(refresh_token_str: str = Query(...), session: Session = Depends(get_session)):
    """刷新 access_token"""
    payload = decode_token(refresh_token_str)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="无效的 refresh_token")
    
    # 检查数据库
    stored = session.exec(
        select(SessionModel).where(SessionModel.refresh_token == refresh_token_str)
    ).first()
    if not stored:
        raise HTTPException(status_code=401, detail="refresh_token 已失效")
    
    user_id = int(payload.get("sub"))
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    
    # 生成新 token
    access_token = create_access_token(user.id, user.email)
    
    return {
        "code": 200,
        "message": "Token 刷新成功",
        "data": {
            "access_token": access_token,
            "expires_in": 3600,
        }
    }

@router.delete("/device")
async def unbind_device(
    device_id: str = Query(...),
    current_user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    """解绑设备"""
    device = session.exec(
        select(UserDevice).where(
            UserDevice.device_id == device_id,
            UserDevice.user_id == current_user.id,
        )
    ).first()
    if device:
        session.delete(device)
        session.commit()
        return {"code": 200, "message": "设备已解绑"}
    return {"code": 200, "message": "设备未绑定，无需解绑"}

def _merge_anonymous_trips(session: Session, user_id: int, device_id: str):
    """合并匿名 trips 到正式用户"""
    anonymous_trips = session.exec(
        select(Trip).where(
            Trip.device_id == device_id,
            Trip.user_id == None,
        )
    ).all()
    
    for trip in anonymous_trips:
        trip.user_id = user_id
    
    return len(anonymous_trips)