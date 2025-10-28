from config.connect_db import mydb
from model.event import Event, EventUpdate, UserInDB
from fastapi import Depends, HTTPException
from services.auth_service import get_current_active_user
import uuid
from datetime import datetime

def admin_required(current_user: UserInDB = Depends(get_current_active_user)):
    if current_user.role not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Unauthorized")
    return current_user

def get_all_events(current_user: UserInDB):
    db = mydb()
    cursor = db.cursor(dictionary=True)
    now = datetime.now()

    if current_user.role == "superadmin":
        cursor.execute("""
            SELECT e.*, 
                   s.id AS survey_id,
                   s.uuid AS survey_uuid,
                   s.name AS survey_title,
                   s.status AS survey_status,
                   s.created_at AS survey_created_at,
                   s.updated_at AS survey_updated_at
            FROM event e
            LEFT JOIN relation_event_survey es ON e.id = es.eventid
            LEFT JOIN survey s ON es.surveyid = s.id
            ORDER BY e.created_at DESC
        """)
    elif current_user.role == "admin":
        cursor.execute("""
            SELECT e.*, 
                   s.id AS survey_id,
                   s.uuid AS survey_uuid,
                   s.name AS survey_title,
                   s.status AS survey_status,
                   s.created_at AS survey_created_at,
                   s.updated_at AS survey_updated_at
            FROM event e
            JOIN relation_user_event rue ON e.id = rue.eventid
            LEFT JOIN relation_event_survey es ON e.id = es.eventid
            LEFT JOIN survey s ON es.surveyid = s.id
            WHERE rue.userid = %s
        """, (current_user.id,))
    else:  # user
        cursor.execute("""
            SELECT DISTINCT e.* FROM event e
            JOIN relation_group_event rge ON e.id = rge.eventid
            JOIN relation_group_user rgu ON rge.groupid = rgu.groupid
            WHERE rgu.userid = %s
        """, (current_user.id,))

    events = cursor.fetchall()
    update_event_list = []
    update_survey_list = []
    formatted_events = []

    for event in events:
        current_status = event["status"]
        start = event.get("time_start")
        end = event.get("time_end")
        uuid_ = event["uuid"]

        if current_status != "archived":
            if end and isinstance(end, datetime) and now > end and current_status != "done":
                event["status"] = "done"
                update_event_list.append(("done", uuid_))
            elif start and isinstance(start, datetime) and now > start and current_status not in ["ongoing", "done"]:
                event["status"] = "ongoing"
                update_event_list.append(("ongoing", uuid_))

        surveys = []
        if end and isinstance(end, datetime) and now > end:
            cursor.execute("""
                SELECT s.uuid FROM survey s
                JOIN relation_event_survey res ON s.id = res.surveyid
                JOIN event e ON res.eventid = e.id
                WHERE e.uuid = %s AND s.status = 'ongoing'
            """, (uuid_,))
            surveys = cursor.fetchall()

        survey_obj = None
        if event.get("survey_id"):
            survey_obj = {
                "survey_id": event["survey_id"],
                "survey_uuid": event["survey_uuid"],
                "name": event["survey_title"],
                "status": event["survey_status"],
                "created_at": event["survey_created_at"],
                "updated_at": event["survey_updated_at"]
            }

        for key in list(event.keys()):
            if key.startswith("survey_"):
                event.pop(key)

        formatted_events.append({
            **event,
            "survey": survey_obj
        })

        for survey in surveys:
            update_survey_list.append(("done", survey["uuid"]))

    for status_val, uuid_ in update_event_list:
        cursor.execute("UPDATE event SET status = %s WHERE uuid = %s", (status_val, uuid_))

    for status_val, uuid_ in update_survey_list:
        cursor.execute("UPDATE survey SET status = %s WHERE uuid = %s", (status_val, uuid_))

    if update_event_list or update_survey_list:
        db.commit()

    cursor.close()
    db.close()

    return {
        "success": True,
        "message": "Events retrieved successfully",
        "count": len(formatted_events),
        "data": formatted_events
    }

def get_event_by_uuid(event_uuid: str):
    db = mydb()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT 
            e.id AS event_id,
            e.uuid AS event_uuid,
            e.name AS event_name,
            e.description AS event_description,
            e.time_start AS event_start_date,
            e.time_end AS event_end_date,
            e.created_at AS event_created_at,
            e.updated_at AS event_updated_at,

            s.id AS survey_id,
            s.uuid AS survey_uuid,
            s.name AS survey_name,
            s.status AS survey_status,
            s.created_at AS survey_created_at,
            s.updated_at AS survey_updated_at
        FROM event e
        LEFT JOIN relation_event_survey es ON e.id = es.eventid
        LEFT JOIN survey s ON es.surveyid = s.id
        WHERE e.uuid = %s
    """, (event_uuid,))

    row = cursor.fetchone()

    if not row:
        cursor.close()
        db.close()
        raise HTTPException(status_code=404, detail="Event not found")

    result = {
        "id": row["event_id"],
        "uuid": row["event_uuid"],
        "name": row["event_name"],
        "description": row["event_description"],
        "start_date": row["event_start_date"],
        "end_date": row["event_end_date"],
        "created_at": row["event_created_at"],
        "updated_at": row["event_updated_at"],
    }

    if row["survey_id"] is not None:
        result["survey"] = {
            "id": row["survey_id"],
            "uuid": row["survey_uuid"],
            "name": row["survey_name"],
            "status": row["survey_status"],
            "created_at": row["survey_created_at"],
            "updated_at": row["survey_updated_at"],
        }

    cursor.close()
    db.close()

    return {
        "success": True,
        "message": "Event retrieved successfully",
        "data": result
    }

def create_event(event: Event, current_user: UserInDB):
    if not event.name or not event.name.strip():
        raise HTTPException(status_code=400, detail="Event name cannot be empty")
    if not event.description or not event.description.strip():
        raise HTTPException(status_code=400, detail="Event description cannot be empty")
    if not event.time_start or not event.time_end:
        raise HTTPException(status_code=400, detail="Event start and end time are required")

    db = mydb()
    cursor = db.cursor()
    new_uuid = str(uuid.uuid4())
    status = "archived"

    cursor.execute(
        """
        INSERT INTO event (uuid, name, time_start, time_end, description, status)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (new_uuid, event.name, event.time_start, event.time_end, event.description, status)
    )

    cursor.execute("SELECT id FROM event WHERE uuid = %s", (new_uuid,))
    event_row = cursor.fetchone()
    if not event_row:
        cursor.close()
        db.close()
        raise HTTPException(status_code=500, detail="Failed to retrieve created event ID")

    event_id = event_row[0]

    cursor.execute(
        "INSERT INTO relation_user_event (userid, eventid) VALUES (%s, %s)",
        (current_user.id, event_id)
    )

    if event.survey_id:
        cursor.execute(
            "INSERT INTO relation_event_survey (eventId, surveyId) VALUES (%s, %s)",
            (event_id, event.survey_id)
        )

    db.commit()
    cursor.close()
    db.close()

    return {
        "success": True,
        "message": "Event created successfully",
        "data":{
        "uuid": new_uuid,
        "name": event.name,
        "time_start": event.time_start,
        "time_end": event.time_end,
        "description": event.description,
        "status": status
        }
    }


def update_event(event_uuid: str, event: EventUpdate):
    db = mydb()
    cursor = db.cursor()

    cursor.execute("SELECT status FROM event WHERE uuid = %s", (event_uuid,))
    row = cursor.fetchone()

    if not row:
        cursor.close()
        db.close()
        raise HTTPException(status_code=404, detail="Event not found")

    current_status = row[0]
    
    if current_status != "archived":
        cursor.close()
        db.close()
        raise HTTPException(status_code=403, detail="Cannot update not archived event")
    
    update_fields = []
    values = []

    if event.name is not None:
        update_fields.append("name = %s")
        values.append(event.name)
    if event.time_start is not None:
        update_fields.append("time_start = %s")
        values.append(event.time_start)
    if event.time_end is not None:
        update_fields.append("time_end = %s")
        values.append(event.time_end)
    if event.description is not None:
        update_fields.append("description = %s")
        values.append(event.description)

    if not update_fields:
        cursor.close()
        db.close()
        raise HTTPException(status_code=400, detail="No fields provided for update")

    update_fields.append("status = %s")
    values.append("archived")

    values.append(event_uuid)
    sql = f"UPDATE event SET {', '.join(update_fields)} WHERE uuid = %s"
    cursor.execute(sql, tuple(values))
    db.commit()

    cursor.close()
    db.close()
    return {"message": "Event updated successfully"}

def publish_event(event_uuid: str, current_user: UserInDB):
    if current_user.role != "superadmin":
        raise HTTPException(status_code=403, detail="Only superadmin can publish events")

    db = mydb()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT status FROM event WHERE uuid = %s", (event_uuid,))
    event = cursor.fetchone()

    if not event:
        cursor.close()
        db.close()
        raise HTTPException(status_code=404, detail="Event not found")

    if event["status"] != "archived":
        cursor.close()
        db.close()
        raise HTTPException(status_code=400, detail="Only archived events can be published")

    cursor.execute("UPDATE event SET status = %s WHERE uuid = %s", ("published", event_uuid))
    db.commit()
    cursor.close()
    db.close()

    return {"message": "Event published successfully"}


def delete_event(event_uuid: str):
    db = mydb()
    cursor = db.cursor()

    cursor.execute("SELECT id FROM event WHERE uuid = %s", (event_uuid,))
    event_row = cursor.fetchone()
    if not event_row:
        cursor.close()
        db.close()
        raise HTTPException(status_code=404, detail="Event not found")

    cursor.execute("DELETE FROM event WHERE uuid = %s", (event_uuid,))
    db.commit()
    cursor.close()
    db.close()
    return {"message": "Event deleted successfully"}

def assign_group_to_event(event_uuid: str, group_uuid: str):
    db = mydb()
    cursor = db.cursor()

    cursor.execute("SELECT id, status FROM event WHERE uuid = %s", (event_uuid,))
    event_row = cursor.fetchone()
    if not event_row:
        cursor.close()
        db.close()
        raise HTTPException(status_code=404, detail="Event not found")
    
    event_id, event_status = event_row

    if event_status in ("ongoing", "done"):
        cursor.close()
        db.close()
        raise HTTPException(status_code=403, detail="Cannot assign group to an ongoing or completed event")

    cursor.execute("SELECT id FROM `group` WHERE uuid = %s", (group_uuid,))
    group_row = cursor.fetchone()
    if not group_row:
        cursor.close()
        db.close()
        raise HTTPException(status_code=404, detail="Group not found")

    group_id = group_row[0]

    cursor.execute("""
        SELECT * FROM relation_group_event
        WHERE groupid = %s AND eventid = %s
    """, (group_id, event_id))
    if cursor.fetchone():
        cursor.close()
        db.close()
        raise HTTPException(status_code=400, detail="Group already assigned to this event")

    cursor.execute(
        "INSERT INTO relation_group_event (groupid, eventid) VALUES (%s, %s)",
        (group_id, event_id)
    )

    db.commit()
    cursor.close()
    db.close()

    return {"message": "Group assigned to event successfully"}
