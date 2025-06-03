from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from services import group_service
from model.group import Group, GroupUpdate, UserInDB
from services.group_service import insert_users_from_csv, admin_required
router = APIRouter()

@router.get("/")
def list_groups(current_user: UserInDB = Depends(admin_required)):
    return group_service.get_all_groups()

@router.get("/{group_uuid}")
def get_group(group_uuid: str, current_user: UserInDB = Depends(admin_required)):
    group = group_service.get_group_by_uuid(group_uuid)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group

@router.post("/")
def create(group: Group, current_user: UserInDB = Depends(admin_required)):
    return group_service.create_group(group)

@router.patch("/{group_uuid}")
def update(group_uuid: str, group: GroupUpdate, current_user: UserInDB = Depends(admin_required)):
    if group_service.is_group_in_active_event(group_uuid):
        raise HTTPException(
            status_code=400,
            detail="User Group tidak bisa diubah selama group ini terpakai di event"
        )
    return group_service.update_group(group_uuid, group)

@router.delete("/{group_uuid}")
def delete(group_uuid: str, current_user: UserInDB = Depends(admin_required)):
    return group_service.delete_group(group_uuid)

@router.post("/upload/users/{group_uuid}")
async def upload_users_from_csv_endpoint(
    group_uuid: str,
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(admin_required)
):
    return insert_users_from_csv(file, group_uuid)

@router.post("/{group_uuid}/assign_user/{user_uuid}")
def assign_user_to_group(
    group_uuid: str,
    user_uuid: str,
    current_user: UserInDB = Depends(admin_required)
):
    return group_service.assign_user_to_group(group_uuid, user_uuid)

@router.delete("/{group_uuid}/remove_user/{user_uuid}")
def remove_user_from_group(
    group_uuid: str,
    user_uuid: str,
    current_user: UserInDB = Depends(admin_required)
):
    return group_service.remove_user_from_group(group_uuid, user_uuid)

