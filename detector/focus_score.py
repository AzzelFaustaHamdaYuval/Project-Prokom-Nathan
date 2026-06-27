"""
detector/focus_score.py
Focus score calculation (0-100) based on accumulated negative events.
"""


CATEGORIES = [
    (85, "Excellent"),
    (70, "Good"),
    (50, "Average"),
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

    # Weight factors (how much each factor reduces focus per second)
    SLEEPY_WEIGHT     = 3.0
    DISTRACT_WEIGHT   = 2.0
    NO_FACE_WEIGHT    = 2.5
    POSTURE_WEIGHT    = 1.0

    penalty = (
        sleepy_duration     * SLEEPY_WEIGHT   +
        distraction_duration* DISTRACT_WEIGHT  +
        no_face_duration    * NO_FACE_WEIGHT   +
        poor_posture_duration * POSTURE_WEIGHT
    )

    # Normalise penalty against total study time
    penalty_ratio = penalty / (study_duration + 1e-6)

    # Map penalty_ratio to score: 0 penalty = 100, high penalty → 0
    score = max(0.0, 100.0 - (penalty_ratio * 50.0))
    return round(min(score, 100.0), 1)


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