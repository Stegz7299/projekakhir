from config.connect_db import mydb
from model.user import UserCreate, UserInDB, TokenData
from utils.security import pwd_context, verify_password
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from config.env import SECRET_KEY, ALGORITHM


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")

def get_db_connection():
    return mydb()

def get_user(username: str) -> Optional[UserInDB]:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
        "SELECT username, email, role, status, password as hashed_password FROM users WHERE username = %s",
        (username,)
    )

        user_data = cursor.fetchone()
        if user_data:
            return UserInDB(**user_data)
        return None
    finally:
        cursor.close()
        conn.close()

def create_user(user: UserCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        hashed_password = pwd_context.hash(user.password)
        cursor.execute(
            "INSERT INTO users (uuid, username, email, password, role, status) VALUES (UUID(), %s, %s, %s, %s, 'active')",
            (user.username, user.email, hashed_password, user.role)
        )
        conn.commit()
        return {"username": user.username, "email": user.email, "role": user.role, "status": "active"}
    finally:
        cursor.close()
        conn.close()


def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

def update_user_in_db(old_username: str, updates: dict):
    conn = get_db_connection()
    cursor = conn.cursor()

    set_clauses = []
    values = []

    for key, value in updates.items():
        set_clauses.append(f"{key} = %s")
        values.append(value)

    set_clause = ", ".join(set_clauses)
    values.append(old_username)

    sql = f"UPDATE users SET {set_clause} WHERE username = %s"

    cursor.execute(sql, tuple(values))
    conn.commit()
    cursor.close()
    conn.close()

async def get_current_active_user(current_user: UserInDB = Depends(get_current_user)):
    return current_user
