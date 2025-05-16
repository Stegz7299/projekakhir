from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from utils.hash_util import hash_filename
from config.connect_db import mydb
from uuid import uuid4
from model.user import FileMetadata
from controllers.auth_controller import get_current_active_user
from model.user import UserInDB
import os

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

router = APIRouter()

@router.post("/upload", response_model=FileMetadata)
async def upload_file(
    name: str = Form(...),
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_active_user)
):
    try:
        content = await file.read()
        file_hash = hash_filename(file.filename + str(uuid4()))
        ext = os.path.splitext(file.filename)[1]
        hashed_filename = f"{file_hash}{ext}"
        file_path = os.path.join(UPLOAD_DIR, hashed_filename)
        url_path = f"http://localhost:8000/{UPLOAD_DIR}/{hashed_filename}"

        with open(file_path, "wb") as f:
            f.write(content)

        conn = mydb()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO images (name, file_hash, file_original, url)
            VALUES (%s, %s, %s, %s)
        """, (name, file_hash, file.filename, url_path))
        conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

    return FileMetadata(
        name=name,
        file_hash=file_hash,
        file_original=file.filename,
        url=url_path
    )
