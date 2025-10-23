from pydantic import BaseModel, EmailStr
from typing import Optional, Any, List,Dict
from datetime import datetime

class Survey(BaseModel):
    name: str
    form: Optional[str]
    status: Optional[str] = "active"

class SurveyInDB(Survey):
    id: int
    uuid: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class AssignSurveyToEvent(BaseModel):
    survey_uuid: str

class SurveyUpdate(BaseModel):
    name: Optional[str] = None
    form: Optional[Any] = None
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
    group_uuid: str
    uuid: str
