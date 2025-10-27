from fastapi import HTTPException
from config.connect_db import mydb
import uuid
from model.recap import Recap, RecapUpdate
from datetime import datetime
from utils.response import success_response

def create_recap(recap: Recap):
    db = mydb()
    cursor = db.cursor()
    recap_uuid = str(uuid.uuid4())

    cursor.execute("""
        INSERT INTO recap (uuid, name, summarize, history_chat, created_at, updated_at)
        VALUES (%s, %s, %s, %s, NOW(), NOW())
    """, (recap_uuid, recap.name, recap.summarize, recap.history_chat))

    db.commit()
    cursor.close()
    db.close()

    return success_response(
            "Recap created successfully",
            {"uuid": recap_uuid, "name": recap.name}
        )


def read_all_recaps():
    db = mydb()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT uuid, name, summarize, history_chat, created_at, updated_at
        FROM recap ORDER BY created_at DESC
    """)
    recaps = cursor.fetchall()

    cursor.close()
    db.close()

    return {
        "status": True,
        "message": "Recap read succesfully",
        "recaps": recaps
    }


def get_recap_by_uuid(recap_uuid: str):
    db = mydb()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT uuid, name, summarize, history_chat, created_at, updated_at
        FROM recap WHERE uuid = %s
    """, (recap_uuid,))
    recap = cursor.fetchone()

    cursor.close()
    db.close()

    if not recap:
        raise HTTPException(status_code=404, detail="Recap not found")

    return {
        "status": True,
        "recap": recap
    }


def update_recap(recap_uuid: str, update_data: RecapUpdate):
    db = mydb()
    cursor = db.cursor()

    fields = []
    values = []

    for key, value in update_data.dict(exclude_unset=True).items():
        fields.append(f"{key} = %s")
        values.append(value)

    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    values.append(recap_uuid)

    cursor.execute(f"""
        UPDATE recap SET {', '.join(fields)}, updated_at = NOW()
        WHERE uuid = %s
    """, tuple(values))

    db.commit()
    cursor.close()
    db.close()

    return {
        "status": True,
        "uuid": recap_uuid,
        "message": "Recap updated successfully"
    }


def delete_recap(recap_uuid: str):
    db = mydb()
    cursor = db.cursor()

    cursor.execute("DELETE FROM recap WHERE uuid = %s", (recap_uuid,))
    db.commit()

    cursor.close()
    db.close()

    return {
        "status": True,
        "uuid": recap_uuid,
        "message": "Recap deleted successfully"
    }
