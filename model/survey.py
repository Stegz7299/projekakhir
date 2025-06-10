from pydantic import BaseModel, EmailStr
from typing import Optional, Any, List,Dict
from datetime import datetime

class Survey(BaseModel):
    name: str
    form: Optional[str]
    setpoint: Optional[int] = None
    status: Optional[str] = "active"

class SurveyInDB(Survey):
    id: int
    uuid: str

class AssignSurveyToEvent(BaseModel):
    survey_uuid: str

class GroupSurveyResponse(BaseModel):
    group_uuid: str
    survey_uuid: str
    user_uuid: str
    answers: List[Dict[str, Any]]  # or a more specific structure

class SurveyUpdate(BaseModel):
    name: Optional[str] = None
    form: Optional[Any] = None
    setpoint: Optional[int] = None
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
