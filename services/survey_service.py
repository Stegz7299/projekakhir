from config.connect_db import mydb
from fastapi import HTTPException
from model.survey import Survey, GroupSurveyResponse, SurveyUpdate, UserInDB
from fastapi.responses import FileResponse
import uuid
from datetime import datetime
import json
from model.survey import Survey
from config.connect_db import mydb
import os
import csv

def get_all_surveys(current_user: UserInDB):
    db = mydb()
    cursor = db.cursor(dictionary=True)

    if current_user.role in ("admin", "superadmin"):
        cursor.execute("""
            SELECT s.* FROM survey s
        """)
    else:
        cursor.execute("""
            SELECT s.* FROM survey s
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

    # Parse form string to JSON to validate it
    try:
        form_obj = json.loads(survey.form) if survey.form else None
        form_str = json.dumps(form_obj) if form_obj else None
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format for form")

    cursor.execute("""
        INSERT INTO survey (uuid, name, form, setpoint, status)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        survey_uuid,
        survey.name,
        form_str,
        survey.setpoint,
        survey.status
    ))

    db.commit()
    cursor.close()
    db.close()

    return {"uuid": survey_uuid, "message": "Survey created successfully"}


def assign_survey_to_event(event_uuid: str, survey_uuid: str):
    db = mydb()
    cursor = db.cursor()

    # Get event ID and status
    cursor.execute("SELECT id, status FROM event WHERE uuid = %s", (event_uuid,))
    event = cursor.fetchone()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event_id, event_status = event

    # Get survey ID
    cursor.execute("SELECT id FROM survey WHERE uuid = %s", (survey_uuid,))
    survey = cursor.fetchone()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    
    survey_id = survey[0]

    # Generate CSV filename
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    csv_filename = f"survey_result_{event_uuid}_{timestamp}.csv"
    csv_path = os.path.join("csv_exports", csv_filename)

    # Create directory and CSV file
    os.makedirs("csv_exports", exist_ok=True)
    with open(csv_path, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["name"] + [str(i) for i in range(1, 11)])

    # Insert into relation_event_survey
    cursor.execute("""
        INSERT INTO relation_event_survey (eventid, surveyid) VALUES (%s, %s)
    """, (event_id, survey_id))
    eventsurveyid = cursor.lastrowid

    # Insert one row per group into relation_group_eventsurvey
    cursor.execute("SELECT id FROM `group`")
    groups = cursor.fetchall()
    for (group_id,) in groups:
        cursor.execute("""
            INSERT INTO relation_group_eventsurvey (groupid, eventsurveyid, file_name)
            VALUES (%s, %s, %s)
        """, (group_id, eventsurveyid, csv_filename))

    # Update survey status if event is ongoing
    if event_status == "ongoing":
        cursor.execute("""
            UPDATE survey SET status = 'ongoing' WHERE id = %s
        """, (survey_id,))

    db.commit()
    cursor.close()
    db.close()

    return {"message": "Survey assigned to event successfully", "csv_file": csv_filename}



def update_survey_by_uuid(survey_uuid: str, update_data: SurveyUpdate):
    db = mydb()
    cursor = db.cursor()

    # Get the survey ID from UUID
    cursor.execute("SELECT id FROM survey WHERE uuid = %s", (survey_uuid,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        db.close()
        raise HTTPException(status_code=404, detail="Survey not found")

    survey_id = row[0]

    # Build update query dynamically
    update_fields = []
    values = []

    if update_data.name is not None:
        update_fields.append("name = %s")
        values.append(update_data.name)
    if update_data.form is not None:
        update_fields.append("form = %s")
        values.append(json.dumps(update_data.form))
    if update_data.setpoint is not None:
        update_fields.append("setpoint = %s")
        values.append(update_data.setpoint)
    if update_data.status is not None:
        update_fields.append("status = %s")
        values.append(update_data.status)

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