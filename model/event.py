from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class Event(BaseModel):
    name: str
    time_start: datetime
    time_end: datetime
    description: Optional[str]
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class EventUpdate(BaseModel):
    name: Optional[str] = None
    time_start: Optional[datetime] = None
    time_end: Optional[datetime] = None
    description: Optional[str] = None
    status: Optional[str] = None

class UserBase(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str
    status: int

class UserInDB(UserBase):
    id : int
    hashed_password: str
    status: int

class AssignGroupToEventByUUID(BaseModel):
    group_uuid: str