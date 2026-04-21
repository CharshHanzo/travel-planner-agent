from pydantic import BaseModel, Field
from typing import Generic, TypeVar, Literal
from enum import Enum

T = TypeVar('T')

class StatusEnum(str, Enum):
    SUCCESS = "success"
    ERROR = "error"

class BaseResponse(BaseModel, Generic[T]):
    status: StatusEnum
    data: T | None = None
    message: str | None = None

class ErrorResponse(BaseModel):
    status: Literal[StatusEnum.ERROR]
    code: str
    message: str
    details: dict | None = None