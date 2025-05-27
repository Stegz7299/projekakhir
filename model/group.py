from pydantic import BaseModel, EmailStr
from typing import Optional

class Group(BaseModel):
    uuid: str
    name: str

class GroupUpdate(BaseModel):
    name: Optional[str] = None

class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: str
    status: int

class UserInDB(UserBase):
    hashed_password: str
    status: int