from config.connect_db import mydb
from model.group import Group, GroupUpdate, UserInDB
import uuid
import csv
import bcrypt
from fastapi import UploadFile, Depends, HTTPException
from services.auth_service import get_current_active_user
from utils.response import success_response, error_response

def admin_required(current_user: UserInDB = Depends(get_current_active_user)):
    if current_user.role not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail=error_response("Unauthorized"))
    return current_user

def get_all_groups():
    db = mydb()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM `group`")
    result = cursor.fetchall()
    cursor.close()
    db.close()
    return success_response("Groups fetched successfully", result)


def get_group_by_uuid(group_uuid: str):
    db = mydb()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM `group` WHERE uuid = %s", (group_uuid,))
    result = cursor.fetchone()
    cursor.close()
    db.close()

    if not result:
        return error_response("Group not found")
    return success_response("Group fetched successfully", result)

def create_group(group: Group):
    try:
        if not group.name or group.name.strip() == "":
            return error_response("Group name cannot be empty")

        db = mydb()
        cursor = db.cursor()
        new_uuid = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO `group` (uuid, name, description) VALUES (%s, %s, %s)",
            (new_uuid, group.name, group.description),
        )
        db.commit()
        cursor.close()
        db.close()
        return success_response(
            "Group created successfully",
            {"uuid": new_uuid, "name": group.name}
        )
    except Exception as e:
        return error_response(f"Failed to create group: {str(e)}")


def update_group(group_uuid: str, group: GroupUpdate):
    db = mydb()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE `group` SET name = %s, description = %s WHERE uuid = %s",
        (group.name, group.description, group_uuid)
    )
    db.commit()
    cursor.close()
    db.close()
    return success_response("Group updated successfully")

def delete_group(group_uuid: str):
    db = mydb()
    cursor = db.cursor()

    cursor.execute("SELECT id FROM `group` WHERE uuid = %s", (group_uuid,))
    group_row = cursor.fetchone()
    if not group_row:
        cursor.close()
        db.close()
        raise HTTPException(status_code=404, detail=error_response("Group not found"))

    group_id = group_row[0]

    cursor.execute("SELECT COUNT(*) FROM relation_group_user WHERE groupId = %s", (group_id,))
    user_count = cursor.fetchone()[0]

    if user_count > 0:
        cursor.close()
        db.close()
        raise HTTPException(
            status_code=400,
            detail=error_response("Cannot delete group: users are still assigned to it")
        )

    cursor.execute("DELETE FROM `group` WHERE id = %s", (group_id,))
    db.commit()

    cursor.close()
    db.close()
    return success_response("Group deleted successfully")


def insert_users_from_csv(file: UploadFile, group_uuid: str):
    try:
        content = file.file.read().decode("utf-8").splitlines()
        reader = csv.DictReader(content)
        conn = mydb()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM `group` WHERE uuid = %s", (group_uuid,))
        group_row = cursor.fetchone()
        if not group_row:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail=error_response("Group not found"))

        group_id = group_row[0]

        for row in reader:
            email = row["email"]
            username = row["username"]
            raw_password = row["password"]

            cursor.execute("SELECT id FROM user WHERE email = %s", (email,))
            if cursor.fetchone():
                continue

            user_uuid = str(uuid.uuid4())
            hashed_password = bcrypt.hashpw(raw_password.encode("utf-8"), bcrypt.gensalt())

            cursor.execute(
                """
                INSERT INTO user (uuid, email, username, password, role, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (user_uuid, email, username, hashed_password, "user", 1),
            )

            user_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO relation_group_user (groupId, userId) VALUES (%s, %s)",
                (group_id, user_id),
            )

        conn.commit()
        cursor.close()
        conn.close()
        return success_response("Users inserted and assigned to group successfully")

    except Exception as e:
        return error_response(f"Error inserting users: {str(e)}")

def assign_user_to_group(group_uuid: str, user_uuid: str):
    if is_group_in_active_event(group_uuid):
        raise HTTPException(
            status_code=403,
            detail=error_response("Cannot assign user to a group that is in an ongoing or completed event")
        )

    conn = mydb()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM user WHERE uuid = %s", (user_uuid,))
    user_row = cursor.fetchone()
    if not user_row:
        raise HTTPException(status_code=404, detail=error_response("User not found"))
    user_id = user_row[0]

    cursor.execute("SELECT id FROM `group` WHERE uuid = %s", (group_uuid,))
    group_row = cursor.fetchone()
    if not group_row:
        raise HTTPException(status_code=404, detail=error_response("Group not found"))
    group_id = group_row[0]

    cursor.execute(
        "SELECT id FROM relation_group_user WHERE groupid = %s AND userid = %s",
        (group_id, user_id)
    )
    if cursor.fetchone():
        return error_response("User already assigned to this group")

    cursor.execute(
        "INSERT INTO relation_group_user (groupid, userid) VALUES (%s, %s)",
        (group_id, user_id)
    )
    conn.commit()

    cursor.close()
    conn.close()

    return success_response("User assigned to group successfully")


def remove_user_from_group(group_uuid: str, user_uuid: str):
    if is_group_in_active_event(group_uuid):
        raise HTTPException(
            status_code=403,
            detail=error_response("Cannot remove user from group that is in an ongoing or completed event")
        )

    conn = mydb()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM `group` WHERE uuid = %s", (group_uuid,))
    group_row = cursor.fetchone()
    if not group_row:
        raise HTTPException(status_code=404, detail=error_response("Group not found"))
    group_id = group_row[0]

    cursor.execute("SELECT id FROM user WHERE uuid = %s", (user_uuid,))
    user_row = cursor.fetchone()
    if not user_row:
        raise HTTPException(status_code=404, detail=error_response("User not found"))
    user_id = user_row[0]

    cursor.execute(
        "SELECT id FROM relation_group_user WHERE groupid = %s AND userid = %s",
        (group_id, user_id)
    )
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail=error_response("User is not assigned to this group"))

    cursor.execute(
        "DELETE FROM relation_group_user WHERE groupid = %s AND userid = %s",
        (group_id, user_id)
    )
    conn.commit()

    cursor.close()
    conn.close()

    return success_response("User removed from group successfully")


def unlink_group_from_event(group_uuid: str, event_uuid: str):
    db = mydb()
    cursor = db.cursor()

    cursor.execute("SELECT id FROM `group` WHERE uuid = %s", (group_uuid,))
    group_row = cursor.fetchone()
    if not group_row:
        raise HTTPException(status_code=404, detail=error_response("Group not found"))
    group_id = group_row[0]

    cursor.execute("SELECT id FROM event WHERE uuid = %s", (event_uuid,))
    event_row = cursor.fetchone()
    if not event_row:
        raise HTTPException(status_code=404, detail=error_response("Event not found"))
    event_id = event_row[0]

    cursor.execute(
        "SELECT id FROM relation_group_event WHERE groupid = %s AND eventid = %s",
        (group_id, event_id)
    )
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail=error_response("Relation not found"))

    cursor.execute(
        "DELETE FROM relation_group_event WHERE groupid = %s AND eventid = %s",
        (group_id, event_id)
    )
    db.commit()

    cursor.close()
    db.close()

    return success_response("Group unlinked from event successfully")


def is_group_in_active_event(group_uuid: str) -> bool:
    db = mydb()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT e.id FROM event e
        JOIN relation_group_event rge ON e.id = rge.eventid
        JOIN `group` g ON rge.groupid = g.id
        WHERE g.uuid = %s AND e.status IN ('ongoing', 'done')
    """, (group_uuid,))
    result = cursor.fetchone()
    cursor.close()
    db.close()
    return result is not None
