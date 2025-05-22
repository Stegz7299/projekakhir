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
    status: int

class UserCreate(UserBase):
    password: str

class UserInDB(UserBase):
    hashed_password: str
    status: int

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
    status: Optional[int] = None

class UserResponse(BaseModel):
    username: str
    email: EmailStr
    role: str
    status: str  # "active" or "inactive"

    @classmethod
    def from_user_in_db(cls, user: UserInDB):
        return cls(
            username=user.username,
            email=user.email,
            role=user.role,
            status="active" if user.status == 1 else "inactive"
        )
