from pydantic import BaseModel
from typing import Optional

class Answer(BaseModel):
    answer_data: str
    event_id: str
    group_id: str
    user_id: str

class AnswerUpdate(BaseModel):
    answer_data: Optional[str] = None