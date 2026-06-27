"""
app.py
StudyFocus AI — Flask backend.
Handles webcam streaming, real-time analysis, session management, and API endpoints.
"""

import cv2
import base64
import time
import threading
import datetime
import os
import json

from flask import (
    Flask, render_template, Response, jsonify,
    request, send_file, abort
)
import numpy as np

# Local modules
from database.db import init_db, save_session, get_all_sessions, get_session_by_id, get_last_7_days
from detector.face_detector    import FaceDetector
from detector.eye_detector     import EyeDetector
from detector.head_detector    import HeadDirectionDetector
from detector.posture_detector import PostureDetector
from detector.focus_score      import calculate_focus_score, get_category, get_suggestions
from detector.pdf_report       import generate_pdf_report

# ─── Flask App ────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config["SECRET_KEY"] = "studyfocus-secret-2024"

# ─── Global Session State ──────────────────────────────────────────────────────
session_lock = threading.Lock()

session_state = {
    "active":             False,
    "start_time":         None,
    "warning_count":      0,
    "face_detector":      None,
    "eye_detector":       None,
    "head_detector":      None,
    "posture_detector":   None,
    # Live stats (updated each frame)
    "face_present":       False,
    "eye_state":          "Unknown",
    "head_direction":     "Forward",
    "posture_state":      "Unknown",
    "focus_score":        100.0,
    "study_duration":     0,
    "sleepy_duration":    0.0,
    "poor_posture_duration": 0.0,
    "distraction_duration":  0.0,
    "no_face_duration":      0.0,
    "last_session_id":    None,
}

# ─── Camera ───────────────────────────────────────────────────────────────────
camera        = None
camera_lock   = threading.Lock()
frame_buffer  = None      # latest JPEG bytes for streaming
analysis_lock = threading.Lock()


def get_camera():
    global camera
    with camera_lock:
        if camera is None or not camera.isOpened():
            camera = cv2.VideoCapture(0)
            camera.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            camera.set(cv2.CAP_PROP_FPS, 15)
    return camera


def release_camera():
    global camera
    with camera_lock:
        if camera is not None:
            camera.release()
            camera = None


# ─── Background Analysis Thread ───────────────────────────────────────────────
def analysis_thread():
    """
    Continuously read frames, run detectors, and update session_state.
    Runs as a daemon thread while session is active.
    """
    global frame_buffer

    while True:
        with session_lock:
            active = session_state["active"]

        if not active:
            time.sleep(0.1)
            continue

        cam = get_camera()
        ret, frame = cam.read()
        if not ret:
            time.sleep(0.05)
            continue

        frame = cv2.flip(frame, 1)
        h, w  = frame.shape[:2]
        rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        with session_lock:
            fd = session_state["face_detector"]
            ed = session_state["eye_detector"]
            hd = session_state["head_detector"]
            pd = session_state["posture_detector"]
            start_t = session_state["start_time"]

        if not all([fd, ed, hd, pd, start_t]):
            time.sleep(0.05)
            continue

        # ── Detections ──────────────────────────────────────────────────
        landmarks = fd.process(rgb)
        posture   = pd.process(rgb)

        face_present    = landmarks is not None
        eye_state       = "Unknown"
        head_direction  = "Forward"

        if face_present:
            eye_state      = ed.process(landmarks, w, h)
            head_direction = hd.process(landmarks, w, h)

        # ── Compute live stats ──────────────────────────────────────────
        now           = time.time()
        elapsed       = int(now - start_t)
        sleepy_dur    = ed.get_sleepy_duration()
        posture_dur   = pd.get_poor_posture_duration()
        distract_dur  = hd.get_distraction_duration()
        no_face_dur   = fd.get_no_face_duration()

        score    = calculate_focus_score(
            elapsed, sleepy_dur, distract_dur, no_face_dur, posture_dur
        )

        # Count warnings
        warning = 0
        if fd.warning_triggered:
            warning += 1
        if pd.warning_triggered:
            warning += 1
        if ed.is_sleepy:
            warning += 1

        # ── Annotate frame ──────────────────────────────────────────────
        # Focus score bar
        bar_w = int((score / 100) * (w - 20))
        cv2.rectangle(frame, (10, h-30), (w-10, h-10), (200, 200, 200), -1)
        bar_color = (100, 220, 100) if score >= 70 else (60, 120, 255) if score >= 50 else (50, 50, 220)
        cv2.rectangle(frame, (10, h-30), (10 + bar_w, h-10), bar_color, -1)
        cv2.putText(frame, f"Focus: {score:.0f}%", (12, h-14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)

        # Status overlay
        status_color = (100, 200, 100) if face_present else (50, 50, 220)
        label = f"Face: {'OK' if face_present else 'NOT DETECTED'}  Eye: {eye_state}  Head: {head_direction}  Posture: {posture}"
        cv2.rectangle(frame, (0, 0), (w, 28), (0, 0, 0), -1)
        cv2.putText(frame, label, (8, 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 200, 220), 1)

        # Warning banner
        if fd.warning_triggered:
            cv2.putText(frame, "⚠ WAJAH TIDAK TERDETEKSI!", (w//2 - 140, h//2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 50, 255), 2)
        if ed.is_sleepy:
            cv2.putText(frame, "😴 KAMU MENGANTUK!", (w//2 - 110, h//2 + 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 100, 255), 2)
        if pd.warning_triggered:
            cv2.putText(frame, "🧍 PERBAIKI POSTUR!", (w//2 - 110, h//2 + 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 150, 200), 2)

        # Encode frame
        _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        frame_buffer = jpeg.tobytes()

        # ── Update shared state ─────────────────────────────────────────
        with session_lock:
            session_state.update({
                "face_present":           face_present,
                "eye_state":              eye_state,
                "head_direction":         head_direction,
                "posture_state":          posture,
                "focus_score":            score,
                "study_duration":         elapsed,
                "sleepy_duration":        sleepy_dur,
                "poor_posture_duration":  posture_dur,
                "distraction_duration":   distract_dur,
                "no_face_duration":       no_face_dur,
                "warning_count":          warning,
            })

        time.sleep(1 / 15)  # ~15 fps


# Start background thread
_thread = threading.Thread(target=analysis_thread, daemon=True)
_thread.start()


# ─── Video Stream Generator ────────────────────────────────────────────────────
def generate_frames():
    """Yield MJPEG frames for the /video_feed route."""
    global frame_buffer
    placeholder = _make_placeholder()
    while True:
        buf = frame_buffer if frame_buffer else placeholder
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf + b"\r\n")
        time.sleep(1 / 15)
        


def _make_placeholder() -> bytes:
    """Return a dark placeholder JPEG when the camera is not active."""
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[:] = (30, 20, 30)
    cv2.putText(img, "Klik 'Mulai Sesi' untuk mengaktifkan kamera",
                (60, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (180, 100, 140), 2)
    _, jpeg = cv2.imencode(".jpg", img)
    return jpeg.tobytes()


# ─── Routes ───────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/history")
def history():
    sessions = get_all_sessions()
    return render_template("history.html", sessions=sessions)


@app.route("/analytics")
def analytics():
    return render_template("analytics.html")

@app.route("/report/<int:session_id>")
def report(session_id):

    session = get_session_by_id(session_id)

    if not session:
        return "Session tidak ditemukan"

    report_data = {
        "student_name": "Nathan",
        "date": session["date"],
        "study_duration": session["study_duration"],
        "session_id": session_id,

        "focus_score": session["focus_score"],
        "eye_focus_percent": 90,
        "head_focus_percent": 85,
        "posture_score": 88,

        "distraction_count": session["warning_count"],
        "look_away_count": 2,
        "eye_closed_count": 1,
        "bad_posture_count": 1,

        "recommendation": "Kurangi distraksi dan lakukan istirahat berkala."
    }

    return render_template(
        "report.html",
        report=report_data
    )

@app.route("/video_feed")
def video_feed():
    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


# ─── Session API ──────────────────────────────────────────────────────────────
@app.route("/api/session/start", methods=["POST"])
def start_session():
    with session_lock:
        if session_state["active"]:
            return jsonify({"status": "already_active"}), 200

        # Initialise detectors
        session_state["face_detector"]    = FaceDetector(no_face_threshold=10.0)
        session_state["eye_detector"]     = EyeDetector()
        session_state["head_detector"]    = HeadDirectionDetector()
        session_state["posture_detector"] = PostureDetector()
        session_state["start_time"]       = time.time()
        session_state["warning_count"]    = 0
        session_state["active"]           = True

    return jsonify({"status": "started"})

current_focus_score = 0
current_eye_state = "Belum Terdeteksi"
current_head_state = "Belum Terdeteksi"
current_posture_state = "Belum Terdeteksi"

from detector.eye_detector import EyeDetector
eye_detector = EyeDetector()

from detector.head_detector import HeadDirectionDetector
head_detector = HeadDirectionDetector()

current_eye_state = eye_detector.eye_state
current_head_state = head_detector.direction


@app.route("/api/session/stop", methods=["POST"])
def stop_session():
    with session_lock:
        if not session_state["active"]:
            return jsonify({"status": "not_active"}), 200

        session_state["active"] = False

        study_dur     = session_state["study_duration"]
        sleepy_dur    = session_state["sleepy_duration"]
        posture_dur   = session_state["poor_posture_duration"]
        distract_dur  = session_state["distraction_duration"]
        no_face_dur   = session_state["no_face_duration"]
        warn_count    = session_state["warning_count"]
        score         = session_state["focus_score"]
        category      = get_category(score)

        # Persist to DB
        data = {
            "date":                   datetime.date.today().isoformat(),
            "study_duration":         study_dur,
            "focus_score":            score,
            "sleepy_duration":        int(sleepy_dur),
            "poor_posture_duration":  int(posture_dur),
            "distraction_duration":   int(distract_dur),
            "warning_count":          warn_count,
            "productivity_category":  category,
        }
        session_id = save_session(data)
        session_state["last_session_id"] = session_id

        # Clean up detectors
        for key in ["face_detector", "eye_detector", "head_detector", "posture_detector"]:
            d = session_state[key]
            if d and hasattr(d, "close"):
                d.close()
            session_state[key] = None

    release_camera()
    return jsonify({"status": "stopped", "session_id": session_id})


@app.route("/api/stats")
def get_stats():
    """Return live session stats as JSON."""
    with session_lock:
        s = session_state
        return jsonify({
            "active":               s["active"],
            "face_present":         s["face_present"],
            "eye_state":            s["eye_state"],
            "head_direction":       s["head_direction"],
            "posture_state":        s["posture_state"],
            "focus_score":          s["focus_score"],
            "study_duration":       s["study_duration"],
            "sleepy_duration":      round(s["sleepy_duration"], 1),
            "poor_posture_duration":round(s["poor_posture_duration"], 1),
            "distraction_duration": round(s["distraction_duration"], 1),
            "warning_count":        s["warning_count"],
            "category":             get_category(s["focus_score"]),
        })


@app.route("/api/sessions")
def api_sessions():
    return jsonify(get_all_sessions())


@app.route("/api/weekly")
def api_weekly():
    return jsonify(get_last_7_days())


@app.route("/api/session/<int:session_id>/report")
def session_report(session_id):
    session = get_session_by_id(session_id)
    if not session:
        abort(404)
    suggestions = get_suggestions(
        session["focus_score"],
        session["sleepy_duration"],
        session.get("distraction_duration", 0),
        session.get("distraction_duration", 0),  # no_face approximation
        session["poor_posture_duration"],
        session["study_duration"],
    )
    return jsonify({"session": session, "suggestions": suggestions})


@app.route("/api/session/<int:session_id>/pdf")
def download_pdf(session_id):
    session = get_session_by_id(session_id)
    if not session:
        abort(404)
    suggestions = get_suggestions(
        session["focus_score"],
        session["sleepy_duration"],
        session.get("distraction_duration", 0),
        session.get("distraction_duration", 0),
        session["poor_posture_duration"],
        session["study_duration"],
    )
    pdf_bytes = generate_pdf_report(session, suggestions)
    import io
    buf = io.BytesIO(pdf_bytes)
    return send_file(
        buf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"StudyFocus_Report_{session_id}.pdf",
    )


@app.route("/api/coach", methods=["POST"])
def ai_coach():
    """
    AI Study Coach endpoint.
    Calls Anthropic API to generate personalised recommendations.
    """
    data    = request.get_json(silent=True) or {}
    score   = data.get("focus_score", 0)
    sleepy  = data.get("sleepy_duration", 0)
    posture = data.get("poor_posture_duration", 0)
    dur     = data.get("study_duration", 0)
    distract= data.get("distraction_duration", 0)

    # Build prompt for Claude
    prompt = f"""
Kamu adalah AI Study Coach yang membantu mahasiswa meningkatkan produktivitas belajar mereka.

Data sesi belajar mahasiswa:
- Total waktu belajar: {dur // 60} menit {dur % 60} detik
- Focus Score: {score:.1f}% ({get_category(score)})
- Durasi mengantuk: {sleepy // 60} menit
- Durasi postur buruk: {posture // 60} menit
- Durasi distraksi: {distract // 60} menit

Berikan 3-4 rekomendasi spesifik dan praktis dalam Bahasa Indonesia untuk membantu mahasiswa ini.
Gunakan nada yang supportif, ramah, dan memotivasi.
Format output sebagai JSON array of strings, contoh:
["Rekomendasi 1...", "Rekomendasi 2...", "Rekomendasi 3..."]
Hanya balas dengan JSON array, tanpa teks lain.
"""

    try:
        import requests as req_lib
        resp = req_lib.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 600,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=20,
        )
        resp.raise_for_status()
        content = resp.json()["content"][0]["text"].strip()
        # Clean up possible markdown fences
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        recommendations = json.loads(content)
    except Exception as e:
        # Fallback to rule-based suggestions
        recommendations = get_suggestions(score, sleepy, distract, distract, posture, dur)

    return jsonify({"recommendations": recommendations})


# ─── Entrypoint ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    app.run(debug=True, threaded=True, host="0.0.0.0", port=5000)

