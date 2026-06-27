import sqlite3

conn = sqlite3.connect("database.db")

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS study_sessions (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    student_name TEXT NOT NULL,

    session_date TEXT NOT NULL,

    study_duration INTEGER,

    focus_score REAL,

    eye_focus_percent REAL,

    head_focus_percent REAL,

    posture_score REAL,

    distraction_count INTEGER,

    look_away_count INTEGER,

    eye_closed_count INTEGER,

    bad_posture_count INTEGER,

    recommendation TEXT

)
""")

conn.commit()
conn.close()

print("Database berhasil dibuat!")