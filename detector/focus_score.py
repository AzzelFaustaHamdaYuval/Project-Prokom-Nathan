"""
detector/focus_score.py
Focus score calculation (0-100) based on accumulated negative events.
"""


CATEGORIES = [
    (90, "Excellent"),
    (75, "Good"),
    (60, "Average"),
    (0,  "Poor"),
]


def calculate_focus_score(
    study_duration: float,
    sleepy_duration: float,
    distraction_duration: float,
    no_face_duration: float,
    poor_posture_duration: float,
) -> float:
    """
    Returns a focus score between 0.0 and 100.0.
    All durations are in seconds.
    """
    if study_duration <= 0:
        return 100.0

    # Hitung rasio tiap kondisi terhadap total waktu belajar
    sleep_ratio = sleepy_duration / study_duration
    distract_ratio = distraction_duration / study_duration
    noface_ratio = no_face_duration / study_duration
    posture_ratio = poor_posture_duration / study_duration
    
    # Bobot penalti (lebih realistis)
    sleep_penalty = sleep_ratio * 35
    distract_penalty = distract_ratio * 25
    noface_penalty = noface_ratio * 20
    posture_penalty = posture_ratio * 15
    
    total_penalty = (
        sleep_penalty +
        distract_penalty +
        noface_penalty +
        posture_penalty
        )
    
    score = 100 - total_penalty
    
    # Bonus jika tidak ada masalah besar
    if sleep_ratio < 0.02:
        score += 2
        
    if noface_ratio < 0.02:
            score += 2
            
    return round(max(0, min(score, 100)), 1)

def get_category(score: float) -> str:
    """Return productivity category string for a given score."""
    for threshold, label in CATEGORIES:
        if score >= threshold:
            return label
    return "Poor"


def get_suggestions(
    score: float,
    sleepy_duration: float,
    distraction_duration: float,
    no_face_duration: float,
    poor_posture_duration: float,
    study_duration: float,
) -> list[str]:
    """Generate personalised improvement suggestions."""
    suggestions = []

    if study_duration > 0:
        if sleepy_duration / study_duration > 0.10:
            suggestions.append(
                "Kamu terdeteksi mengantuk selama sesi ini. Coba tidur cukup malam sebelumnya dan pastikan ruangan memiliki sirkulasi udara yang baik."
            )
        if distraction_duration / study_duration > 0.15:
            suggestions.append(
                "Frekuensi melihat ke arah lain cukup tinggi. Singkirkan gangguan visual seperti ponsel dan coba teknik Pomodoro (25 menit fokus, 5 menit istirahat)."
            )
        if no_face_duration / study_duration > 0.10:
            suggestions.append(
                "Terdeteksi sering tidak ada di depan kamera. Pastikan kamu duduk pada jarak yang tepat dari layar dan hindari meninggalkan meja belajar terlalu sering."
            )
        if poor_posture_duration / study_duration > 0.20:
            suggestions.append(
                "Postur tubuh perlu diperbaiki. Atur kursi dan meja agar punggung tegak, layar sejajar mata, dan kaki rata di lantai."
            )

    if score >= 85:
        suggestions.append("Pertahankan konsistensi belajarmu — kamu sudah sangat fokus hari ini!")
    elif score >= 70:
        suggestions.append("Sesi belajarmu cukup baik. Sedikit peningkatan konsistensi akan mendorongmu ke level Excellent.")
    elif score < 50:
        suggestions.append("Coba mulai sesi belajar lebih singkat (30 menit) dengan istirahat teratur untuk membangun kebiasaan fokus.")

    return suggestions if suggestions else ["Terus pertahankan kebiasaan belajar yang baik!"]