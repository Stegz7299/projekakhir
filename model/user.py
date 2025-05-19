from pydantic import BaseModel, EmailStr
from typing import Optional

class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: str

class UserCreate(UserBase):
    password: str

class UserInDB(UserBase):
    hashed_password: str
    status: str

class User(UserBase):
    pass

class FileMetadata(BaseModel):
    name: str
    file_hash: str
    file_original: str
    url: str

class UserUpdate(BaseModel):
    username: str 
    new_username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    old_password: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None