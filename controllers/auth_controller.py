from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from model.user import LoginRequest, Token, User, UserCreate, UserInDB, UserResponse, UserUpdate
from services.auth_service import (
    authenticate_user,
    create_user,
    get_user,
    create_access_token,
    get_current_active_user,
    verify_password,
    update_user_in_db,
    get_all_users,
    get_user_by_email,
    get_user_by_uuid,
    set_user_status_by_uuid
)
from datetime import timedelta
from typing import List, Optional
from config.env import ACCESS_TOKEN_EXPIRE_MINUTES
from utils.security import pwd_context
from utils.response import success_response, error_response
from services.token_blacklist import blacklist_token

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")

@router.post("/login")
async def login_for_access_token(login_data: LoginRequest):
    try:
        user = authenticate_user(login_data.username, login_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Incorrect username or password"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        if user.status != 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"message": "Account is inactive. Please contact the administrator."},
            )

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": user.username,
                "user_id": user.id,
                "name": user.username,
                "email": user.email,
                "role": user.role
            },
            expires_delta=access_token_expires,
        )

        user_data = user.__dict__.copy()
        for key in ["hashed_password", "role", "status", "id", "uuid"]:
            user_data.pop(key, None)

        user_data["authorization"] = {"token": access_token}

        return success_response("Login successfully", user_data)
    
    except Exception as e:
        return error_response(f"Failed to login: {str(e)}", 500)


@router.post("/users")
async def register_user(
    user: UserCreate,
    current_user: UserInDB = Depends(get_current_active_user)
):
    if current_user.role not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Only admins can register new users"}
        )

    existing_user = get_user(user.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Username already registered"}
        )

    existing_email = get_user_by_email(user.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Email already registered"}
        )

    created_user = create_user(user)
    return success_response("User registered successfully", created_user)


@router.patch("/update/{uuid}")
async def update_user(
    uuid: str,
    update_data: UserUpdate,
    current_user: UserInDB = Depends(get_current_active_user)
):
    target_user = get_user_by_uuid(uuid)
    if not target_user:
        raise HTTPException(status_code=404, detail={"message": "User not found"})

    updates = {}
    if current_user.role == "superadmin":
        if update_data.new_username and update_data.new_username != target_user["username"]:
            if get_user(update_data.new_username):
                raise HTTPException(status_code=409, detail={"message": "Username already exists"})
            updates["username"] = update_data.new_username

        if update_data.email and update_data.email != target_user["email"]:
            if get_user_by_email(update_data.email):
                raise HTTPException(status_code=409, detail={"message": "Email already exists"})
            updates["email"] = update_data.email

        if update_data.role:
            updates["role"] = update_data.role
        if update_data.password:
            updates["password"] = pwd_context.hash(update_data.password)
        if update_data.status is not None:
            updates["status"] = update_data.status

    elif current_user.role == "admin":
        if target_user["role"] == "superadmin":
            raise HTTPException(status_code=403, detail={"message": "You can't update a superadmin"})

        if update_data.new_username and update_data.new_username != target_user["username"]:
            if get_user(update_data.new_username):
                raise HTTPException(status_code=409, detail={"message": "Username already exists"})
            updates["username"] = update_data.new_username

        if update_data.email and update_data.email != target_user["email"]:
            if get_user_by_email(update_data.email):
                raise HTTPException(status_code=409, detail={"message": "Email already exists"})
            updates["email"] = update_data.email

        if update_data.role:
            if update_data.role == "superadmin":
                raise HTTPException(status_code=403, detail={"message": "Admins cannot assign 'superadmin' role"})
            updates["role"] = update_data.role

        if update_data.password:
            updates["password"] = pwd_context.hash(update_data.password)
        if update_data.status is not None:
            updates["status"] = update_data.status

    elif current_user.uuid == uuid:
        if not update_data.password:
            raise HTTPException(status_code=403, detail={"message": "Only password update is allowed for users"})
        if not update_data.old_password:
            raise HTTPException(status_code=400, detail={"message": "Old password is required"})
        if not verify_password(update_data.old_password, target_user["hashed_password"]):
            raise HTTPException(status_code=401, detail={"message": "Old password is incorrect"})
        updates["password"] = pwd_context.hash(update_data.password)
    else:
        raise HTTPException(status_code=403, detail={"message": "You don't have permission"})

    if not updates:
        raise HTTPException(status_code=400, detail={"message": "No valid fields to update"})

    update_user_in_db(uuid, updates)
    updated_username = updates.get("username", target_user["username"])
    updated_user_data = get_user(updated_username)

    return success_response("User updated successfully", UserResponse.from_user_in_db(updated_user_data))


@router.delete("/users/{uuid}/close")
async def close_user_account(uuid: str, current_user: UserInDB = Depends(get_current_active_user)):
    if current_user.role not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail={"message": "You don't have permission"})

    target_user = get_user_by_uuid(uuid)
    if not target_user:
        raise HTTPException(status_code=404, detail={"message": "User not found"})

    if target_user["status"] == 0:
        raise HTTPException(status_code=400, detail={"message": "User already inactive"})

    if current_user.role == "admin" and target_user["role"] == "superadmin":
        raise HTTPException(status_code=403, detail={"message": "Admins cannot deactivate superadmins"})

    set_user_status_by_uuid(uuid, 0)
    return success_response(f"User '{target_user['username']}' has been deactivated.")


@router.post("/logout")
async def logout(request: Request, token: str = Depends(oauth2_scheme)):
    blacklist_token(token)
    return success_response("Successfully logged out")


@router.get("/users/me/")
async def read_users_me(current_user: UserInDB = Depends(get_current_active_user)):
    return success_response("Fetched current user data", UserResponse.from_user_in_db(current_user))


@router.get("/users/{uuid}")
async def get_user_by_uuid_route(uuid: str, current_user: UserInDB = Depends(get_current_active_user)):
    user_data = get_user_by_uuid(uuid)
    if not user_data:
        raise HTTPException(status_code=404, detail={"message": "User not found"})
    if current_user.role not in ["admin", "superadmin"] and current_user.uuid != uuid:
        raise HTTPException(status_code=403, detail={"message": "Access denied"})

    formatted_user = {
        "username": user_data["username"],
        "email": user_data["email"],
        "role": user_data["role"],
        "status": "active" if user_data["status"] == 1 else "inactive",
        "group": {
            "id": user_data.get("id"),
            "name": user_data.get("name")
        }
    }

    return success_response("User fetched successfully", formatted_user)


@router.get("/users")
async def list_all_users(current_user: UserInDB = Depends(get_current_active_user)):
    users_in_db = get_all_users()
    formatted = [UserResponse.from_user_in_db(user) for user in users_in_db]
    return success_response("All users fetched successfully", formatted)
