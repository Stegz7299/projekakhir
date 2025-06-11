from fastapi import APIRouter, Depends
from model.event import Event, EventUpdate, UserInDB, AssignGroupToEventByUUID
from services import event_service
from services.auth_service import get_current_active_user

router = APIRouter()

@router.get("/")
def get_all_events(current_user: UserInDB = Depends(get_current_active_user)):
    return event_service.get_all_events(current_user)

@router.get("/{event_uuid}")
def get_event_by_uuid(event_uuid: str, current_user: UserInDB = Depends(get_current_active_user)):
    return event_service.get_event_by_uuid(event_uuid, current_user)

@router.post("/")
def create_event(event: Event, current_user: UserInDB = Depends(event_service.admin_required)):
    return event_service.create_event(event, current_user)

@router.patch("/{event_uuid}")
def update_event(event_uuid: str, event: EventUpdate, current_user: UserInDB = Depends(event_service.admin_required)):
    return event_service.update_event(event_uuid, event)

@router.patch("/{event_uuid}/publish")
def publish_event(event_uuid: str, current_user: UserInDB = Depends(event_service.admin_required)):
    return event_service.publish_event(event_uuid, current_user)

@router.delete("/{event_uuid}")
def delete_event(event_uuid: str, current_user: UserInDB = Depends(event_service.admin_required)):
    return event_service.delete_event(event_uuid)

@router.post("/{event_uuid}/assign_group")
def assign_group_to_event(
    event_uuid: str,
    payload: AssignGroupToEventByUUID,
    current_user: UserInDB = Depends(event_service.admin_required)
):
    return event_service.assign_group_to_event(event_uuid, payload.group_uuid)
