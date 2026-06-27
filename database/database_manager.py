import sqlite3

DATABASE = "database.db"

def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

from database.database_manager import get_connection

def save_session(data):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO study_sessions(

        student_name,
        session_date,
        study_duration,
        focus_score,
        eye_focus_percent,
        head_focus_percent,
        posture_score,
        distraction_count,
        look_away_count,
        eye_closed_count,
        bad_posture_count,
        recommendation

    )
    VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
    """, (

        data["student_name"],
        data["session_date"],
        data["study_duration"],
        data["focus_score"],
        data["eye_focus_percent"],
        data["head_focus_percent"],
        data["posture_score"],
        data["distraction_count"],
        data["look_away_count"],
        data["eye_closed_count"],
        data["bad_posture_count"],
        data["recommendation"]

    ))

    conn.commit()
    conn.close()

def get_all_sessions():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM study_sessions
    ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    conn.close()

    return rows

def get_analytics():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        AVG(focus_score) as avg_focus,
        SUM(study_duration) as total_duration,
        SUM(distraction_count) as total_distraction
    FROM study_sessions
    """)

    result = cursor.fetchone()

    conn.close()

    return result