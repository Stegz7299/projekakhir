from fastapi import APIRouter, Depends, HTTPException
from model.survey import Survey, AssignSurveyToEvent, SurveyUpdate
from model.event import UserInDB
from services import survey_service
from services.event_service import admin_required
from fastapi.responses import FileResponse
from services.auth_service import get_current_active_user

router = APIRouter()

@router.get("/")
def get_all_surveys(current_user: UserInDB = Depends(get_current_active_user)):
    return survey_service.get_all_surveys(current_user)

@router.get("/{survey_uuid}")
def get_survey_by_uuid(survey_uuid: str, current_user: UserInDB = Depends(get_current_active_user)):
    return survey_service.get_survey_by_uuid(survey_uuid, current_user)

@router.post("/")
def create_survey(survey: Survey, current_user: UserInDB = Depends(admin_required)):
    return survey_service.create_survey(survey)

@router.post("/{event_uuid}/assign_survey")
def assign_survey_to_event(event_uuid: str, payload: AssignSurveyToEvent, current_user: UserInDB = Depends(admin_required)):
    return survey_service.assign_survey_to_event(event_uuid, payload.survey_uuid)

@router.patch("/{survey_uuid}")
def update_survey_by_uuid(
    survey_uuid: str,
    update_data: SurveyUpdate,
    current_user: UserInDB = Depends(admin_required)
):
    return survey_service.update_survey_by_uuid(survey_uuid, update_data)