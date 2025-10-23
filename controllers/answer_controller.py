from fastapi import APIRouter, Depends
from model.answer import Answer, AnswerUpdate
from services import answer_service
from model.event import UserInDB
from services.auth_service import get_current_active_user
from services.event_service import admin_required

router = APIRouter()

@router.post("/")
def create_answer(answer: Answer, current_user: UserInDB = Depends(get_current_active_user)):
    return answer_service.create_answer(answer)

@router.get("/")
def get_all_answers(current_user: UserInDB = Depends(get_current_active_user)):
    return answer_service.get_all_answers()

@router.get("/answers/{uuid}")
def get_answer_by_uuid(uuid: str, current_user: UserInDB = Depends(get_current_active_user)):
    return answer_service.get_answer_by_uuid(uuid, current_user)

@router.get("/answers/event/{survey_id}")
def get_answers_by_event(survey_id: int, current_user: UserInDB = Depends(get_current_active_user)):
    return answer_service.get_answers_by_event(survey_id, current_user)

@router.get("/answers/event/{survey_id}/group/{group_id}")
def get_answers_by_event_and_group(survey_id: int, group_id: int, current_user: UserInDB = Depends(get_current_active_user)):
    return answer_service.get_answers_by_event_and_group(survey_id, group_id, current_user)

@router.get("/{answer_uuid}")
def get_answer_by_uuid(answer_uuid: str, current_user: UserInDB = Depends(get_current_active_user)):
    return answer_service.get_answer_by_uuid(answer_uuid)

@router.patch("/{answer_uuid}")
def update_answer(answer_uuid: str, update_data: AnswerUpdate, current_user: UserInDB = Depends(admin_required)):
    return answer_service.update_answer(answer_uuid, update_data)

@router.delete("/{answer_uuid}")
def delete_answer(answer_uuid: str, current_user: UserInDB = Depends(admin_required)):
    return answer_service.delete_answer(answer_uuid)
