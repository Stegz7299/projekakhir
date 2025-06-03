from config.connect_db import mydb
from model.group import Group, GroupUpdate, UserInDB
import uuid
import csv
import uuid
import bcrypt
from fastapi import UploadFile, Depends,HTTPException
from services.auth_service import get_current_active_user

def admin_required(current_user: UserInDB = Depends(get_current_active_user)):
    if current_user.role not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Unauthorized")
    return current_user

def get_all_groups():
    db = mydb()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM `group`")
    result = cursor.fetchall()
    cursor.close()
    db.close()
    return result

def get_group_by_uuid(group_uuid: str):
    db = mydb()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM `group` WHERE uuid = %s", (group_uuid,))
    result = cursor.fetchone()
    cursor.close()
    db.close()
    return result

def create_group(group: Group):
    db = mydb()
    cursor = db.cursor()
    new_uuid = str(uuid.uuid4())
    cursor.execute("INSERT INTO `group` (uuid, name) VALUES (%s, %s)", (new_uuid, group.name))
    db.commit()
    cursor.close()
    db.close()
    return {"uuid": new_uuid, "name": group.name}

def update_group(group_uuid: str, group: GroupUpdate):
    db = mydb()
    cursor = db.cursor()
    if group.name:
        cursor.execute("UPDATE `group` SET name = %s WHERE uuid = %s", (group.name, group_uuid))
    db.commit()
    cursor.close()
    db.close()
    return {"message": "Group updated successfully"}

def delete_group(group_uuid: str):
    db = mydb()
    cursor = db.cursor()

    # Get group ID by UUID
    cursor.execute("SELECT id FROM `group` WHERE uuid = %s", (group_uuid,))
    group_row = cursor.fetchone()
    if not group_row:
        cursor.close()
        db.close()
        raise HTTPException(status_code=404, detail="Group not found")

    group_id = group_row[0]

    # Check if users are still assigned to the group
    cursor.execute("SELECT COUNT(*) FROM relation_group_user WHERE groupId = %s", (group_id,))
    user_count = cursor.fetchone()[0]

    if user_count > 0:
        cursor.close()
        db.close()
        raise HTTPException(
            status_code=400,
            detail="Cannot delete group: users are still assigned to it"
        )

    # Safe to delete
    cursor.execute("DELETE FROM `group` WHERE id = %s", (group_id,))
    db.commit()

    cursor.close()
    db.close()
    return {"message": "Group deleted successfully"}


def insert_users_from_csv(file: UploadFile, group_uuid: str):
    try:
        content = file.file.read().decode("utf-8").splitlines()
        reader = csv.DictReader(content)
        conn = mydb()
        cursor = conn.cursor()

        # 🔍 Resolve group_id from group_uuid
        cursor.execute("SELECT id FROM `group` WHERE uuid = %s", (group_uuid,))
        group_row = cursor.fetchone()
        if not group_row:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Group not found")

        group_id = group_row[0]

        for row in reader:
            email = row["email"]
            username = row["username"]
            raw_password = row["password"]

            # Cek apakah user dengan email sudah ada
            cursor.execute("SELECT id FROM user WHERE email = %s", (email,))
            existing_user = cursor.fetchone()
            if existing_user:
                continue  # skip user yang sudah ada

            # Insert user
            user_uuid = str(uuid.uuid4())
            hashed_password = bcrypt.hashpw(raw_password.encode('utf-8'), bcrypt.gensalt())
            role = "user"
            status = 1

            cursor.execute("""
                INSERT INTO user (uuid, email, username, password, role, status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_uuid, email, username, hashed_password, role, status))

            user_id = cursor.lastrowid

            # Insert into relation_group_user
            cursor.execute("""
                INSERT INTO relation_group_user (groupId, userId)
                VALUES (%s, %s)
            """, (group_id, user_id))

        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "Users inserted and assigned to group successfully."}

    except Exception as e:
        return {"error": str(e)}

    
def assign_user_to_group(group_uuid: str, user_uuid: str):
    # 🔒 Check if group is in an active or done event
    if is_group_in_active_event(group_uuid):
        raise HTTPException(
            status_code=403,
            detail="Cannot assign user to a group that is in an ongoing or completed event"
        )

    conn = mydb()
    cursor = conn.cursor()

    # 🔍 Get user ID from UUID
    cursor.execute("SELECT id FROM user WHERE uuid = %s", (user_uuid,))
    user_row = cursor.fetchone()
    if not user_row:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    user_id = user_row[0]

    # 🔍 Get group ID from UUID
    cursor.execute("SELECT id FROM `group` WHERE uuid = %s", (group_uuid,))
    group_row = cursor.fetchone()
    if not group_row:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Group not found")
    group_id = group_row[0]

    # ❌ Check if already assigned
    cursor.execute("""
        SELECT id FROM relation_group_user 
        WHERE groupid = %s AND userid = %s
    """, (group_id, user_id))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return {"message": "User already assigned to this group."}

    # ✅ Assign user to group
    cursor.execute("""
        INSERT INTO relation_group_user (groupid, userid)
        VALUES (%s, %s)
    """, (group_id, user_id))
    conn.commit()

    cursor.close()
    conn.close()

    return {"message": "User assigned to group successfully."}


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

def remove_user_from_group(group_uuid: str, user_uuid: str):
    # ❌ Block removal if group is in an ongoing or done event
    if is_group_in_active_event(group_uuid):
        raise HTTPException(
            status_code=403,
            detail="Cannot remove user from group that is in an ongoing or completed event"
        )

    conn = mydb()
    cursor = conn.cursor()

    # Get group ID from UUID
    cursor.execute("SELECT id FROM `group` WHERE uuid = %s", (group_uuid,))
    group_row = cursor.fetchone()
    if not group_row:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Group not found")
    group_id = group_row[0]

    # Get user ID from UUID
    cursor.execute("SELECT id FROM user WHERE uuid = %s", (user_uuid,))
    user_row = cursor.fetchone()
    if not user_row:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    user_id = user_row[0]

    # Check if relation exists
    cursor.execute("""
        SELECT id FROM relation_group_user 
        WHERE groupid = %s AND userid = %s
    """, (group_id, user_id))
    relation_row = cursor.fetchone()
    if not relation_row:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="User is not assigned to this group")

    # Delete the relation
    cursor.execute("""
        DELETE FROM relation_group_user 
        WHERE groupid = %s AND userid = %s
    """, (group_id, user_id))
    conn.commit()

    cursor.close()
    conn.close()

    return {"message": "User removed from group successfully."}
