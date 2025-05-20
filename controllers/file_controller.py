from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Path
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

@router.patch("/upload/{id}", response_model=FileMetadata)
async def update_file_metadata(
    id: int = Path(..., description="The ID of the image record in the database"),
    name: str = Form(...),
    file: UploadFile = File(None),
    current_user: UserInDB = Depends(get_current_active_user)
):
    conn = mydb()
    cursor = conn.cursor()

    try:
        # Fetch existing record by ID
        cursor.execute("SELECT file_hash, file_original, url FROM images WHERE id = %s", (id,))
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="File not found")

        file_hash, old_filename, old_url = result
        new_file_name = old_filename
        new_url = old_url

        # If a new file is provided
        if file:
            content = await file.read()
            ext = os.path.splitext(file.filename)[1]
            new_filename = f"{file_hash}{ext}"
            file_path = os.path.join(UPLOAD_DIR, new_filename)
            new_url = f"http://localhost:8000/{UPLOAD_DIR}/{new_filename}"

            with open(file_path, "wb") as f:
                f.write(content)

            new_file_name = file.filename

        # Update DB record
        cursor.execute("""
            UPDATE images
            SET name = %s, file_original = %s, url = %s
            WHERE id = %s
        """, (name, new_file_name, new_url, id))
        conn.commit()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

    return FileMetadata(
        name=name,
        file_hash=file_hash,
        file_original=new_file_name,
        url=new_url
    )

@router.delete("/upload/{id}", status_code=204)
async def delete_file_by_id(
    id: int = Path(..., description="ID of the image to delete"),
    current_user: UserInDB = Depends(get_current_active_user)
):
    conn = mydb()
    cursor = conn.cursor()

    try:
        # Check if the record exists
        cursor.execute("SELECT file_hash, file_original FROM images WHERE id = %s", (id,))
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Image not found")

        file_hash, original_filename = result
        ext = os.path.splitext(original_filename)[1]
        file_path = os.path.join(UPLOAD_DIR, f"{file_hash}{ext}")

        # Delete the file from disk if it exists
        if os.path.exists(file_path):
            os.remove(file_path)

        # Delete the record from the database
        cursor.execute("DELETE FROM images WHERE id = %s", (id,))
        conn.commit()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()