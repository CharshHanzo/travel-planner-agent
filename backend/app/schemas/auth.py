from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=20)
    username: Optional[str] = Field(None, max_length=50)
    device_id: Optional[str] = Field(None, max_length=255)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False
    device_id: Optional[str] = Field(None, max_length=255)

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600

class UserInfo(BaseModel):
    id: int
    email: str
    username: str
    avatar: Optional[str] = None

class AuthResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: Optional[dict] = None