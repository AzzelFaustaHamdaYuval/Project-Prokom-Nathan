"""
detector/posture_detector.py
Posture detection using MediaPipe Pose landmarks.
"""

import mediapipe as mp
import numpy as np
import time

SLOUCH_THRESHOLD = 18.0   # degrees of shoulder tilt considered slouching
SLOUCH_WARN_SEC  = 30.0   # warn after slouching for this many seconds
MIN_SLOUCH_FRAMES = 5


class PostureDetector:
    """Detect good/poor posture from shoulder alignment."""

    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=0,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        self._slouch_start: float | None = None
        self.poor_posture_duration: float = 0.0
        self.posture_state: str = "Good"
        self.warning_triggered: bool = False
        self.slouch_frames: int = 0
        

    def process(self, rgb_frame):
        """
        Process RGB frame with MediaPipe Pose.
        Returns posture_state: 'Good' or 'Poor'
        """
        results = self.pose.process(rgb_frame)
        now = time.time()

        if not results.pose_landmarks:
            # Can't determine posture — treat as good to avoid false positives
            self.posture_state = "Unknown"
            return self.posture_state

        lms = results.pose_landmarks.landmark
        left_shoulder  = lms[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = lms[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]

        # Angle of shoulder line relative to horizontal
        dx = right_shoulder.x - left_shoulder.x
        dy = right_shoulder.y - left_shoulder.y
        angle = abs(np.degrees(np.arctan2(dy, dx)))

        # Also check forward head: compare ear y vs shoulder y
        left_ear  = lms[self.mp_pose.PoseLandmark.LEFT_EAR]
        right_ear = lms[self.mp_pose.PoseLandmark.RIGHT_EAR]
        ear_y     = (left_ear.y + right_ear.y) / 2.0
        shoulder_y= (left_shoulder.y + right_shoulder.y) / 2.0
        head_forward = ear_y > shoulder_y - 0.03  # head drooping toward shoulders

        is_poor = (angle > SLOUCH_THRESHOLD) or head_forward

        if is_poor:
            self.slouch_frames += 1
            if self.slouch_frames >= MIN_SLOUCH_FRAMES:
                self.posture_state = "Poor"
                if self._slouch_start is None:
                    self._slouch_start = now
                
                elapsed = now - self._slouch_start
                if elapsed >= SLOUCH_WARN_SEC:
                    self.warning_triggered = True
                    
        else:
            self.slouch_frames = 0
            self.posture_state = "Good"
            if self._slouch_start is not None:
                self.poor_posture_duration += now - self._slouch_start
                self._slouch_start = None

            self.warning_triggered = False
            self.slouch_frames = 0

        return self.posture_state

    def get_poor_posture_duration(self) -> float:
        if self._slouch_start is not None:
            return self.poor_posture_duration + (time.time() - self._slouch_start)
        return self.poor_posture_duration

    def reset(self):
        self._slouch_start = None
        self.poor_posture_duration = 0.0
        self.posture_state = "Good"
        self.warning_triggered = False
        self.slouch_frames = 0

    def close(self):
        self.pose.close()