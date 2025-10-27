from config.connect_db import mydb
from fastapi import HTTPException
from model.survey import Survey, SurveyUpdate, UserInDB
import uuid
import json
from model.survey import Survey
from config.connect_db import mydb

def get_all_surveys(current_user: UserInDB):
    db = mydb()
    cursor = db.cursor(dictionary=True)

    if current_user.role in ("admin", "superadmin"):
        cursor.execute("""
            SELECT s.name, s.uuid FROM survey s
        """)
    else:
        cursor.execute("""
            SELECT s.name FROM survey s
            JOIN relation_event_survey res ON s.id = res.surveyid
            JOIN event e ON res.eventid = e.id
            WHERE e.status = 'ongoing' AND s.status = 'ongoing'
        """)

    surveys = cursor.fetchall()
    cursor.close()
    db.close()
    return surveys

def get_survey_by_uuid(survey_uuid: str, current_user: UserInDB):
    db = mydb()
    cursor = db.cursor(dictionary=True)

    if current_user.role in ("admin", "superadmin"):
        cursor.execute("SELECT * FROM survey WHERE uuid = %s", (survey_uuid,))
    else:
        cursor.execute("""
            SELECT s.* FROM survey s
            JOIN relation_event_survey res ON s.id = res.surveyid
            JOIN event e ON res.eventid = e.id
            WHERE s.uuid = %s AND e.status = 'ongoing' AND s.status = 'ongoing'
        """, (survey_uuid,))

    survey = cursor.fetchone()

    cursor.close()
    db.close()

    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found or not accessible")

    return survey

def create_survey(survey: Survey):
    db = mydb()
    cursor = db.cursor()
    survey_uuid = str(uuid.uuid4())

    try:
        form_obj = json.loads(survey.form) if survey.form else None
        form_str = json.dumps(form_obj) if form_obj else None
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format for form")

    cursor.execute("""
        INSERT INTO survey (uuid, name, form, status, created_at, updated_at)
        VALUES (%s, %s, %s, %s, NOW(), NOW())
    """, (
    survey_uuid,
    survey.name,
    form_str,
    survey.status
    ))


    db.commit()
    cursor.close()
    db.close()

    return {"uuid": survey_uuid, "message": "Survey created successfully"}


def assign_survey_to_event(event_uuid: str, survey_uuid: str):
    db = mydb()
    cursor = db.cursor()

    cursor.execute("SELECT id, status FROM event WHERE uuid = %s", (event_uuid,))
    event = cursor.fetchone()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event_id, event_status = event

    cursor.execute("SELECT id FROM survey WHERE uuid = %s", (survey_uuid,))
    survey = cursor.fetchone()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    
    survey_id = survey[0]

    cursor.execute("""
        INSERT INTO relation_event_survey (eventid, surveyid) VALUES (%s, %s)
    """, (event_id, survey_id))
    
    if event_status == "ongoing":
        cursor.execute("""
            UPDATE survey SET status = 'ongoing' WHERE id = %s
        """, (survey_id,))

    db.commit()
    cursor.close()
    db.close()

    return {"message": "Survey assigned to event successfully"}



def update_survey_by_uuid(survey_uuid: str, update_data: SurveyUpdate):
    db = mydb()
    cursor = db.cursor()

    cursor.execute("SELECT id FROM survey WHERE uuid = %s", (survey_uuid,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        db.close()
        raise HTTPException(status_code=404, detail="Survey not found")

    survey_id = row[0]

    update_fields = []
    values = []

    if update_data.name is not None:
        update_fields.append("name = %s")
        values.append(update_data.name)
    if update_data.form is not None:
        update_fields.append("form = %s")
        values.append(json.dumps(update_data.form))
    if update_data.status is not None:
        update_fields.append("status = %s")
        values.append(update_data.status)

    update_fields.append("updated_at = NOW()")

    if not update_fields:
        cursor.close()
        db.close()
        raise HTTPException(status_code=400, detail="No fields to update")

    values.append(survey_id)
    sql = f"UPDATE survey SET {', '.join(update_fields)} WHERE id = %s"
    cursor.execute(sql, tuple(values))

    db.commit()
    cursor.close()
    db.close()

    return {"message": "Survey updated successfully"}