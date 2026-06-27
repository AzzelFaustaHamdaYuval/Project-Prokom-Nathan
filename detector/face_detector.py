"""
detector/face_detector.py
Face presence detection using MediaPipe Face Mesh.
"""

import mediapipe as mp
import time


class FaceDetector:
    """Detect whether a face is present in the frame."""

    def __init__(self, no_face_threshold: float = 10.0):
        """
        Args:
            no_face_threshold: Seconds without a face before triggering a warning.
        """
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.no_face_threshold = no_face_threshold
        self._no_face_start: float | None = None
        self.no_face_duration: float = 0.0  # cumulative seconds without face
        self.warning_triggered: bool = False
        self.last_landmarks = None

    def process(self, rgb_frame):
        """
        Process an RGB frame and return face landmarks (or None).
        Updates internal timers for no-face duration.
        """
        results = self.face_mesh.process(rgb_frame)
        now = time.time()

        if results.multi_face_landmarks:
            self.last_landmarks = results.multi_face_landmarks[0]
            if self._no_face_start is not None:
                # Face returned — accumulate no-face time
                self.no_face_duration += now - self._no_face_start
                self._no_face_start = None
            self.warning_triggered = False
            return self.last_landmarks
        else:
            self.last_landmarks = None
            if self._no_face_start is None:
                self._no_face_start = now
            elapsed = now - self._no_face_start
            if elapsed >= self.no_face_threshold:
                self.warning_triggered = True
            return None

    def get_no_face_duration(self) -> float:
        """Return total accumulated seconds where no face was detected."""
        if self._no_face_start is not None:
            return self.no_face_duration + (time.time() - self._no_face_start)
        return self.no_face_duration

    def reset(self):
        """Reset all counters (call at start of new session)."""
        self._no_face_start = None
        self.no_face_duration = 0.0
        self.warning_triggered = False
        self.last_landmarks = None

    def close(self):
        self.face_mesh.close()