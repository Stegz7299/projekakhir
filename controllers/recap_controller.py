from fastapi import APIRouter, Depends
from model.event import UserInDB
from model.recap import Recap, RecapUpdate
from services import recap_service
from services.auth_service import get_current_active_user
from services.event_service import admin_required

router = APIRouter()

@router.post("/")
def create_recap(data: Recap, current_user: UserInDB = Depends(admin_required)):
    return recap_service.create_recap(data)

@router.get("/")
def get_all_recaps(current_user: UserInDB = Depends(get_current_active_user)):
    return recap_service.read_all_recaps()

@router.get("/{recap_uuid}")
def get_recap_by_uuid(recap_uuid: str, current_user: UserInDB = Depends(get_current_active_user)):
    return recap_service.get_recap_by_uuid(recap_uuid)

@router.patch("/{recap_uuid}")
def update_recap(recap_uuid: str, update_data: RecapUpdate, current_user: UserInDB = Depends(admin_required)):
    return recap_service.update_recap(recap_uuid, update_data)

@router.delete("/{recap_uuid}")
def delete_recap(recap_uuid: str, current_user: UserInDB = Depends(admin_required)):
    return recap_service.delete_recap(recap_uuid)
