from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Recap(BaseModel):
    name: str
    summarize: Optional[str] = None
    history_chat: Optional[str] = None

class RecapUpdate(BaseModel):
    name: Optional[str] = None
    summarize: Optional[str] = None
    history_chat: Optional[str] = None

class RecapInDB(Recap):
    id: int
    uuid: str
    created_at: datetime
    updated_at: datetime