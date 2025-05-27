from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from model.user import LoginRequest, Token, User, UserCreate, UserInDB, UserResponse
from services.auth_service import (
    authenticate_user,
    create_user,
    get_user,
    create_access_token,
    get_current_active_user,
    verify_password,
    update_user_in_db,
    get_all_users,
    get_user_by_email
)
from datetime import timedelta
from typing import Optional
from config.env import ACCESS_TOKEN_EXPIRE_MINUTES
from model.user import UserUpdate
from utils.security import pwd_context
from typing import List
from services.token_blacklist import blacklist_token

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")

@router.post("/login", response_model=Token)
async def login_for_access_token(login_data: LoginRequest):
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
        data={"sub": user.username},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=User)
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
    return created_user


@router.patch("/update", response_model=UserResponse)
async def update_user(
    update_data: UserUpdate,
    current_user: UserInDB = Depends(get_current_active_user)
):
    target_user = get_user(update_data.username)
    if not target_user:
        raise HTTPException(status_code=404, detail={"message": "User not found"})

    updates = {}

    # 1. SUPERADMIN – Full access
    if current_user.role == "superadmin":
        if update_data.new_username and update_data.new_username != target_user.username:
            if get_user(update_data.new_username):
                raise HTTPException(status_code=409, detail={"message": "Username already exists"})
            updates["username"] = update_data.new_username

        if update_data.email and update_data.email != target_user.email:
            if get_user(update_data.email):
                raise HTTPException(status_code=409, detail={"message": "Email already exists"})
            updates["email"] = update_data.email

        if update_data.role:
            updates["role"] = update_data.role
        if update_data.password:
            updates["password"] = pwd_context.hash(update_data.password)
        if update_data.status is not None:
            updates["status"] = update_data.status

    # 2. ADMIN – Limited access
    elif current_user.role == "admin":
        # Cannot update superadmin accounts
        if target_user.role == "superadmin":
            raise HTTPException(status_code=403, detail={"message": "You can't update a superadmin"})

        if update_data.new_username and update_data.new_username != target_user.username:
            if get_user(update_data.new_username):
                raise HTTPException(status_code=409, detail={"message": "Username already exists"})
            updates["username"] = update_data.new_username

        if update_data.email and update_data.email != target_user.email:
            if get_user(update_data.email):
                raise HTTPException(status_code=409, detail={"message": "Email already exists"})
            updates["email"] = update_data.email

        # Cannot assign or elevate to superadmin
        if update_data.role:
            if update_data.role == "superadmin":
                raise HTTPException(status_code=403, detail={"message": "Admins cannot assign 'superadmin' role"})
            updates["role"] = update_data.role

        if update_data.password:
            updates["password"] = pwd_context.hash(update_data.password)
        if update_data.status is not None:
            updates["status"] = update_data.status

    # 3. REGULAR USER – Only allowed to update own password
    elif current_user.username == update_data.username:
        if not update_data.password:
            raise HTTPException(
                status_code=403,
                detail={"message": "Only password update is allowed for users"}
            )

        if not update_data.old_password:
            raise HTTPException(
                status_code=400,
                detail={"message": "Old password is required to change your password"}
            )

        if not verify_password(update_data.old_password, target_user.hashed_password):
            raise HTTPException(
                status_code=401,
                detail={"message": "Old password is incorrect"}
            )

        updates["password"] = pwd_context.hash(update_data.password)

    else:
        raise HTTPException(
            status_code=403,
            detail={"message": "You don't have permission to update this user"}
        )

    if not updates:
        raise HTTPException(
            status_code=400,
            detail={"message": "No valid fields to update"}
        )

    # Validate merged data before updating
    temp_data = target_user.dict()
    temp_data.update(updates)

    try:
        User(**temp_data)
    except Exception as e:
        raise HTTPException(status_code=422, detail={"message": f"Validation failed: {str(e)}"})

    # Update in database
    update_user_in_db(update_data.username, updates)

    updated_username = update_data.new_username or update_data.username
    updated_user_data = get_user(updated_username)

    if not updated_user_data:
        raise HTTPException(status_code=404, detail={"message": "You could only update the password"})

    return UserResponse.from_user_in_db(updated_user_data)


@router.post("/logout")
async def logout(request: Request, token: str = Depends(oauth2_scheme)):
    blacklist_token(token)
    return {"message": "Successfully logged out"}

@router.get("/users/me/", response_model=UserResponse)
async def read_users_me(current_user: UserInDB = Depends(get_current_active_user)):
    return UserResponse.from_user_in_db(current_user)

@router.get("/users", response_model=list[UserResponse])
async def list_all_users(current_user: UserInDB = Depends(get_current_active_user)):
    users_in_db = get_all_users()
    return [UserResponse.from_user_in_db(user) for user in users_in_db]
