from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, description="Username cannot be empty")
    password: str = Field(..., min_length=1, description="Password cannot be empty")

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
    id:int
    hashed_password: str
    status: int
    uuid:str

class User(UserBase):
    pass

class FileMetadata(BaseModel):
    name: str
    file_hash: str
    file_original: str
    url: str

class UserUpdate(BaseModel):
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
