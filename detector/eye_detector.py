"""
detector/eye_detector.py
Eye openness (drowsiness) detection using MediaPipe Face Mesh landmarks.
"""

import time
import numpy as np


# MediaPipe Face Mesh landmark indices for Eye Aspect Ratio (EAR)
LEFT_EYE_INDICES  = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380]

EAR_THRESHOLD    = 0.20   # below this → eyes closed
CLOSED_DURATION  = 2.0    # seconds of closed eyes before "sleepy"

EAR_HISTORY_SIZE = 5
MIN_CLOSED_FRAMES = 3


def _eye_aspect_ratio(landmarks, eye_indices, frame_w: int, frame_h: int) -> float:
    """Compute the Eye Aspect Ratio (EAR) for a given set of landmark indices."""
    pts = []
    for idx in eye_indices:
        lm = landmarks.landmark[idx]
        pts.append(np.array([lm.x * frame_w, lm.y * frame_h]))

    # Vertical distances
    A = np.linalg.norm(pts[1] - pts[5])
    B = np.linalg.norm(pts[2] - pts[4])
    # Horizontal distance
    C = np.linalg.norm(pts[0] - pts[3])

    ear = (A + B) / (2.0 * C + 1e-6)
    return float(ear)


class EyeDetector:
    """Track eye state and accumulate sleepy duration."""

    def __init__(self):
        self._closed_start: float | None = None
        self.sleepy_duration: float = 0.0   # total seconds with eyes closed
        self.is_sleepy: bool = False
        self.eye_state: str = "Open"        # "Open" or "Closed"

        self.closed_frames = 0
        self.ear_history = []

    def process(self, landmarks, frame_w: int, frame_h: int):
        """
        Update eye state given MediaPipe face landmarks.
        Returns current eye_state string.
        """
        if landmarks is None:
            self.eye_state = "Unknown"
            return self.eye_state
    
        now = time.time()

        left_ear  = _eye_aspect_ratio(landmarks, LEFT_EYE_INDICES,  frame_w, frame_h)
        right_ear = _eye_aspect_ratio(landmarks, RIGHT_EYE_INDICES, frame_w, frame_h)
        avg_ear   = (left_ear + right_ear) / 2.0

        self.ear_history.append(avg_ear)
        if len(self.ear_history) > EAR_HISTORY_SIZE:
             self.ear_history.pop(0)
             
        avg_ear = sum(self.ear_history) / len(self.ear_history)

        if avg_ear < EAR_THRESHOLD:
            self.closed_frames += 1
            if self.closed_frames >= MIN_CLOSED_FRAMES:
                self.eye_state = "Closed"
                if self._closed_start is None:
                    self._closed_start = now

                elapsed = now - self._closed_start
                
                if elapsed >= CLOSED_DURATION:
                    self.is_sleepy = True
        else:
            self.closed_frames = 0
            self.eye_state = "Open"
            
            if self._closed_start is not None:
                self.sleepy_duration += now - self._closed_start
                self._closed_start = None

                self.is_sleepy = False
                
        return self.eye_state

    def get_sleepy_duration(self) -> float:
        """Return total accumulated sleepy seconds (eyes closed)."""
        if self._closed_start is not None:
            return self.sleepy_duration + (time.time() - self._closed_start)
        return self.sleepy_duration

    def reset(self):
        self._closed_start = None
        self.sleepy_duration = 0.0
        self.is_sleepy = False
        self.eye_state = "Open"

        self.closed_frames = 0
        self.ear_history.clear()



        