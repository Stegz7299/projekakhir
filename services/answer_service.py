from fastapi import HTTPException
from config.connect_db import mydb
from model.answer import Answer, AnswerUpdate
import uuid


def create_answer(answer: Answer):
    db = mydb()
    cursor = db.cursor()

    new_uuid = str(uuid.uuid4())

    cursor.execute("""
        INSERT INTO answers (uuid, answer_data, created_at, updated_at)
        VALUES (%s, %s, NOW(), NOW())
    """, (new_uuid, answer.answer_data))
    answer_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO relation_answer_user (answerid, userid)
        VALUES (%s, %s)
    """, (answer_id, answer.user_id))

    cursor.execute("""
        INSERT INTO relation_answer_group (answerid, groupid)
        VALUES (%s, %s)
    """, (answer_id, answer.group_id))

    cursor.execute("""
        INSERT INTO relation_answer_events (answerid, eventid)
        VALUES (%s, %s)
    """, (answer_id, answer.event_id))

    db.commit()
    cursor.close()
    db.close()

    return {
        "status": "success",
        "message": "Answer created successfully",
        "data": {
            "uuid": new_uuid,
            "user_id": answer.user_id,
            "group_id": answer.group_id,
            "event_id": answer.event_id
        }
    }


def get_all_answers():
    db = mydb()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            a.uuid, a.answer_data, 
            rae.eventid AS event_id,
            rag.groupid AS group_id,
            rau.userid AS user_id,
            a.created_at, a.updated_at
        FROM answers a
        LEFT JOIN relation_answer_events rae ON a.id = rae.answerid
        LEFT JOIN relation_answer_group rag ON a.id = rag.answerid
        LEFT JOIN relation_answer_user rau ON a.id = rau.answerid
        ORDER BY a.created_at DESC
    """)
    results = cursor.fetchall()

    cursor.close()
    db.close()

    return {
        "status": "success",
        "message": "Answers retrieved successfully",
        "data": results
    }


def get_answer_by_uuid(answer_uuid: str):
    db = mydb()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            a.uuid,
            a.answer_data,
            rae.eventid AS event_id,
            rag.groupid AS group_id,
            rau.userid AS user_id,
            a.created_at, a.updated_at
        FROM answers a
        LEFT JOIN relation_answer_events rae ON a.id = rae.answerid
        LEFT JOIN relation_answer_group rag ON a.id = rag.answerid
        LEFT JOIN relation_answer_user rau ON a.id = rau.answerid
        WHERE a.uuid = %s
    """, (answer_uuid,))
    result = cursor.fetchone()

    cursor.close()
    db.close()

    if not result:
        raise HTTPException(status_code=404, detail="Answer not found")

    return {
        "status": "success",
        "message": "Answer retrieved successfully",
        "data": result
    }


def get_answers_by_event(survey_id: int, current_user):
    db = mydb()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT sa.*, g.name AS group_name, u.username AS user_name
        FROM survey_answer sa
        JOIN `group` g ON sa.group_id = g.id
        JOIN user u ON sa.user_id = u.id
        WHERE sa.survey_id = %s
    """, (survey_id,))
    results = cursor.fetchall()

    cursor.close()
    db.close()

    return {
        "status": "success",
        "message": "Answers retrieved successfully for survey",
        "data": results
    }


def get_answers_by_event_and_group(survey_id: int, group_id: int, current_user):
    db = mydb()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT sa.*, u.username AS user_name
        FROM survey_answer sa
        JOIN user u ON sa.user_id = u.id
        WHERE sa.survey_id = %s AND sa.group_id = %s
    """, (survey_id, group_id))
    results = cursor.fetchall()

    cursor.close()
    db.close()

    return {
        "status": "success",
        "message": "Answers retrieved successfully for group",
        "data": results
    }


def update_answer(answer_uuid: str, update_data: AnswerUpdate):
    db = mydb()
    cursor = db.cursor()

    cursor.execute("SELECT id FROM answers WHERE uuid = %s", (answer_uuid,))
    existing = cursor.fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Answer not found")

    cursor.execute("""
        UPDATE answers 
        SET answer_data = %s, updated_at = NOW() 
        WHERE uuid = %s
    """, (update_data.answer_data, answer_uuid))
    db.commit()

    cursor.close()
    db.close()

    return {
        "status": "success",
        "message": "Answer updated successfully",
        "data": {"uuid": answer_uuid}
    }


def delete_answer(answer_uuid: str):
    db = mydb()
    cursor = db.cursor()

    cursor.execute("SELECT id FROM answers WHERE uuid = %s", (answer_uuid,))
    answer = cursor.fetchone()
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")

    answer_id = answer[0]

    cursor.execute("DELETE FROM relation_answer_user WHERE answerid = %s", (answer_id,))
    cursor.execute("DELETE FROM relation_answer_group WHERE answerid = %s", (answer_id,))
    cursor.execute("DELETE FROM relation_answer_events WHERE answerid = %s", (answer_id,))

    cursor.execute("DELETE FROM answers WHERE id = %s", (answer_id,))
    db.commit()

    cursor.close()
    db.close()

    return {
        "status": "success",
        "message": "Answer deleted successfully",
        "data": {"uuid": answer_uuid}
    }
