"""The grayscale Haar face/eye method from PanTilt/FaceTracking.py.

Only detection is reused. Camera pose stays fixed for the stereo calibration.
"""
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


MODELS = Path(__file__).resolve().parent.parent/'PreTrainedModels'


@dataclass
class FaceCandidate:
    center: np.ndarray
    box: tuple
    area: float
    eyes: tuple


class FaceDetector:
    def __init__(self, face_path=MODELS/'face.xml', eye_path=MODELS/'eye.xml',
                 scale_factor=1.3, min_neighbors=5):
        if not np.isfinite(scale_factor) or scale_factor <= 1 or min_neighbors < 0:
            raise ValueError('Face scale factor must exceed 1 and min neighbors must be nonnegative.')
        self.face = cv2.CascadeClassifier(str(face_path))
        self.eye = cv2.CascadeClassifier(str(eye_path))
        if self.face.empty():
            raise ValueError(f'Could not load face cascade: {face_path}')
        if self.eye.empty():
            raise ValueError(f'Could not load eye cascade: {eye_path}')
        self.scale_factor = scale_factor
        self.min_neighbors = min_neighbors

    def __call__(self, frame, settings=None, roi=None):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        height, width = gray.shape
        x0, y0, x1, y1 = 0, 0, width, height
        if roi is not None:
            x, y, w, h = map(int, roi)
            x0, y0, x1, y1 = max(0, x), max(0, y), min(width, x+w), min(height, y+h)
        mask = np.zeros_like(gray)
        if x1 <= x0 or y1 <= y0:
            return [], mask
        # Same call and default parameters as FaceTracking.py, without resizing
        # the observations away from their calibrated native pixel geometry.
        boxes = self.face.detectMultiScale(gray[y0:y1, x0:x1], self.scale_factor, self.min_neighbors)
        candidates = []
        for x, y, w, h in sorted(boxes, key=lambda b: b[2]*b[3], reverse=True)[:6]:
            x, y, w, h = int(x)+x0, int(y)+y0, int(w), int(h)
            eyes = self.eye.detectMultiScale(gray[y:y+h, x:x+w])
            absolute_eyes = tuple((x+int(ex), y+int(ey), int(ew), int(eh)) for ex, ey, ew, eh in eyes)
            candidates.append(FaceCandidate(np.array([x+w//2, y+h//2], dtype=float),
                                             (x, y, w, h), float(w*h), absolute_eyes))
            mask[y:y+h, x:x+w] = 255
        return candidates, mask
