"""
detector/head_detector.py
Head direction detection using MediaPipe Face Mesh nose-tip & chin landmarks.
"""

import time
import numpy as np


# Key landmark indices
NOSE_TIP    = 1
CHIN        = 199
LEFT_EAR    = 234
RIGHT_EAR   = 454
LEFT_EYE    = 33
RIGHT_EYE   = 263

LOOK_AWAY_THRESHOLD = 5.0  # seconds of looking away before penalising focus


class HeadDirectionDetector:
    """Estimate head direction from face landmarks."""

    def __init__(self):
        self._away_start: float | None = None
        self.distraction_duration: float = 0.0  # total seconds looking away
        self.direction: str = "Forward"

    def process(self, landmarks, frame_w: int, frame_h: int) -> str:
        """
        Determine head direction and update distraction timer.
        Returns one of: 'Forward', 'Left', 'Right', 'Down'
        """
        def lm(idx):
            l = landmarks.landmark[idx]
            return np.array([l.x * frame_w, l.y * frame_h])

        nose   = lm(NOSE_TIP)
        left_e = lm(LEFT_EYE)
        right_e= lm(RIGHT_EYE)
        chin   = lm(CHIN)

        eye_center  = (left_e + right_e) / 2.0
        eye_width   = np.linalg.norm(right_e - left_e)

        # Horizontal deviation: nose vs eye midpoint
        horizontal_offset = (nose[0] - eye_center[0]) / (eye_width + 1e-6)

        # Vertical: chin below eye-center relative to eye width
        vertical_offset   = (chin[1] - eye_center[1]) / (eye_width + 1e-6)

        if horizontal_offset < -0.20:
            direction = "Right"   # face turned so nose points to the left of screen = head right
        elif horizontal_offset > 0.20:
            direction = "Left"
        elif vertical_offset < 1.2:
            direction = "Down"
        else:
            direction = "Forward"

        self.direction = direction
        now = time.time()

        if direction != "Forward":
            if self._away_start is None:
                self._away_start = now
        else:
            if self._away_start is not None:
                self.distraction_duration += now - self._away_start
                self._away_start = None

        return direction

    def get_distraction_duration(self) -> float:
        if self._away_start is not None:
            return self.distraction_duration + (time.time() - self._away_start)
        return self.distraction_duration

    def reset(self):
        self._away_start = None
        self.distraction_duration = 0.0
        self.direction = "Forward"