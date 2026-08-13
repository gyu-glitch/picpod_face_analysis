"""MediaPipe FaceLandmarker(Tasks API) 랜드마크 추출 + 롤 보정.

- 478 랜드마크 + 블렌드셰이프 (웃음 감지 경고 — v1 설계 재현)
- face_landmarker.task 모델은 최초 실행 시 models/로 자동 다운로드
"""
from pathlib import Path

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    FaceLandmarker, FaceLandmarkerOptions, RunningMode,
)

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)
MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "face_landmarker.task"

SMILE_BLENDSHAPES = ("mouthSmileLeft", "mouthSmileRight")
SMILE_THRESHOLD = 0.5

_landmarker: FaceLandmarker | None = None


class FaceDetectionError(Exception):
    """얼굴 0개 또는 2개 이상 — API에서 422로 변환."""


def _ensure_model() -> Path:
    if not MODEL_PATH.exists():
        import urllib.request
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        print(f"face_landmarker.task 다운로드 중 → {MODEL_PATH}")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    return MODEL_PATH


def _get_landmarker() -> FaceLandmarker:
    global _landmarker
    if _landmarker is None:
        options = FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(_ensure_model())),
            running_mode=RunningMode.IMAGE,
            num_faces=2,
            output_face_blendshapes=True,
        )
        _landmarker = FaceLandmarker.create_from_options(options)
    return _landmarker


def extract_landmarks(image_bgr: np.ndarray) -> tuple[np.ndarray, list[str]]:
    """얼굴 1개의 478 랜드마크 (x, y) 픽셀 좌표(롤 보정)와 경고 목록 반환."""
    h, w = image_bgr.shape[:2]
    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB),
    )
    result = _get_landmarker().detect(mp_image)

    faces = result.face_landmarks or []
    if len(faces) == 0:
        raise FaceDetectionError("얼굴이 인식되지 않았습니다.")
    if len(faces) > 1:
        raise FaceDetectionError("얼굴이 2개 이상 인식되었습니다. 한 명만 촬영해 주세요.")

    warnings = []
    if result.face_blendshapes:
        smile = max(
            (c.score for c in result.face_blendshapes[0] if c.category_name in SMILE_BLENDSHAPES),
            default=0.0,
        )
        if smile > SMILE_THRESHOLD:
            warnings.append("웃는 표정이 감지되었습니다. 무표정 사진이 더 정확합니다.")

    pts = np.array([(lm.x * w, lm.y * h) for lm in faces[0]], dtype=np.float64)
    return _correct_roll(pts), warnings


def _correct_roll(pts: np.ndarray) -> np.ndarray:
    """양쪽 눈 중심이 수평이 되도록 전체 좌표를 회전."""
    left_eye = pts[[33, 133, 159, 145]].mean(axis=0)
    right_eye = pts[[362, 263, 386, 374]].mean(axis=0)
    dx, dy = right_eye - left_eye
    angle = np.arctan2(dy, dx)
    center = pts.mean(axis=0)
    c, s = np.cos(-angle), np.sin(-angle)
    rot = np.array([[c, -s], [s, c]])
    return (pts - center) @ rot.T + center
