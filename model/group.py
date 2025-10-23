from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class Group(BaseModel):
    uuid: Optional[str] = None
    name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: str
    status: int

class UserInDB(UserBase):
    hashed_password: str
    status: int