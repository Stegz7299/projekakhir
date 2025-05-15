from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from model.user import LoginRequest, Token, User, UserCreate, UserInDB
from services.auth_service import (
    authenticate_user,
    create_user,
    get_user,
    create_access_token,
    get_current_active_user
)
from datetime import timedelta
from typing import Optional
from config.env import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")

@router.post("/login", response_model=Token)
async def login_for_access_token(login_data: LoginRequest):
    user = authenticate_user(login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
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
    if current_user.role.lower() != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can register new users"
        )

    existing_user = get_user(user.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    created_user = create_user(user)
    return created_user

@router.get("/users/me/", response_model=User)
async def read_users_me(current_user: UserInDB = Depends(get_current_active_user)):
    return User(username=current_user.username, email=current_user.email, role=current_user.role)

@router.get("/users/me/items")
async def read_own_items(current_user: UserInDB = Depends(get_current_active_user)):
    return [{
        "item_id": 1,
        "owner": {
            "username": current_user.username,
            "email": current_user.email,
            "role": current_user.role
        }
    }]
