from config.connect_db import mydb
from model.user import UserCreate, UserInDB, TokenData
from utils.security import pwd_context, verify_password
from jose import JWTError, jwt, ExpiredSignatureError
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from config.env import SECRET_KEY, ALGORITHM
from model.user import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")

def get_db_connection():
    return mydb()

def get_user(username: str) -> Optional[UserInDB]:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT 
            u.id, u.username, u.email, u.role, u.status, 
            u.password AS hashed_password, 
            u.uuid, g.uuid AS group_uuid
            FROM user u
            LEFT JOIN `group` g ON u.id = g.id
            WHERE u.username = %s

            """,
            (username,)
        )
        user_data = cursor.fetchone()
        if user_data:
            return UserInDB(**user_data)
        return None
    finally:
        cursor.close()
        conn.close()

def get_user_by_uuid(uuid: str) -> Optional[UserInDB]:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT 
                u.id, u.username, u.email, u.role, u.status, 
                u.password AS hashed_password, u.uuid,
                g.id AS id, g.name AS name
            FROM user u
            LEFT JOIN relation_group_user rgu ON u.id = rgu.userid
            LEFT JOIN `group` g ON rgu.groupid = g.id
            WHERE u.uuid = %s
            """,
            (uuid,)
        )
        user_data = cursor.fetchone()
        if user_data:
            return user_data  # Return full dictionary for custom response
        return None
    finally:
        cursor.close()
        conn.close()

def get_user_by_email(email: str) -> Optional[UserInDB]:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, username, email, role, status, password as hashed_password FROM user WHERE email = %s",
            (email,)
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
            "INSERT INTO user (uuid, username, email, password, role, status) VALUES (UUID(), %s, %s, %s, %s, 1)",
            (user.username, user.email, hashed_password, user.role)
        )
        conn.commit()
        return {"username": user.username, "email": user.email, "role": user.role, "status": 1}
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
    from services.token_blacklist import is_token_blacklisted

    if is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Token has been revoked. Please log in again."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"message": "Could not validate credentials"},
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Token has expired. Please log in again."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise credentials_exception

    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception

    return user

def update_user_in_db(uuid: str, updates: dict):
    conn = get_db_connection()
    cursor = conn.cursor()

    set_clauses = []
    values = []

    for key, value in updates.items():
        set_clauses.append(f"{key} = %s")
        values.append(value)

    set_clause = ", ".join(set_clauses)
    values.append(uuid)

    sql = f"UPDATE user SET {set_clause} WHERE uuid = %s"

    cursor.execute(sql, tuple(values))
    conn.commit()
    cursor.close()
    conn.close()

def set_user_status_by_uuid(uuid: str, status: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    sql = "UPDATE user SET status = %s WHERE uuid = %s"
    cursor.execute(sql, (status, uuid))
    conn.commit()

    cursor.close()
    conn.close()
    
async def get_current_active_user(current_user: UserInDB = Depends(get_current_user)):
    return current_user

def get_all_users() -> list[User]:
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT username, email, role, status FROM user")
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    users = [
        User(
            username=row["username"],
            email=row["email"],
            role=row["role"],
            status=row.get("status", 0)  # ← return as integer
        )
        for row in rows
    ]
    return users
