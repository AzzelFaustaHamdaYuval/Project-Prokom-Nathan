"""
database/db.py
SQLite database setup and helper functions for StudyFocus AI.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "studyfocus.db")


def get_connection():
    """Return a connection to the SQLite database."""
    conn = sqlite3.connect(
        DB_PATH,
        timeout=10,
        check_same_thread=False
        )
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database and create tables if they don't exist."""
    with get_connection() as conn:
        cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            study_duration INTEGER DEFAULT 0,      -- in seconds
            focus_score REAL DEFAULT 0.0,
            sleepy_duration INTEGER DEFAULT 0,     -- in seconds
            poor_posture_duration INTEGER DEFAULT 0, -- in seconds
            distraction_duration INTEGER DEFAULT 0,  -- in seconds
            no_face_duration INTEGER DEFAULT 0,
            warning_count INTEGER DEFAULT 0,
            productivity_category TEXT DEFAULT 'Poor',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_datE
        ON sessions(date)
    """)

    conn.commit()
    conn.close()
    import logging
    
    logging.info("Database initialized.")


def save_session(data: dict) -> int:
    """
    Save a completed study session to the database.
    Returns the inserted row id.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sessions
            (date, study_duration, focus_score, sleepy_duration,
             poor_posture_duration, distraction_duration, no_face_duration, warning_count, productivity_category)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("date"),
        data.get("study_duration", 0),
        data.get("focus_score", 0.0),
        data.get("sleepy_duration", 0),
        data.get("poor_posture_duration", 0),
        data.get("distraction_duration", 0),
        data.get("no_face_duration", 0),
        data.get("warning_count", 0),
        data.get("productivity_category", "Poor"),
    ))
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def get_all_sessions():
    """Retrieve all sessions ordered by newest first."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions ORDER BY created_at DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_session_by_id(session_id: int):
    """Retrieve a single session by its ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_last_7_days():
    """Retrieve aggregated daily data for the last 7 days."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            date,
            ROUND(AVG(focus_score), 1) AS avg_focus,
            SUM(study_duration) AS total_study,
            COUNT(*) AS session_count
        FROM sessions
        WHERE date >= date('now', '-6 days')
        GROUP BY date
        ORDER BY date ASC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows