"""분석 파이프라인 오케스트레이션: 이미지 → FaceAnalysis (+ 페르소나 해석)."""
import uuid
from datetime import datetime, timezone

import numpy as np

from .landmarks import extract_landmarks
from .features import compute_features
from .bucketize import bucketize
from .scoring import score_samjeong, score_ohaeng, compute_life_graph
from .type_table import resolve_type
from .schemas import FaceAnalysis

RAW_KEYS = [
    "face_ratio", "upper_zone", "mid_zone", "lower_zone", "brow_angle",
    "glabella_width", "eye_width", "eye_height", "eye_tilt", "cheekbone_width",
    "nose_length", "nose_width", "philtrum", "mouth_width", "jaw_length",
    "jaw_width", "symmetry",
]


def analyze_image(image_bgr: np.ndarray, analysis_id: str | None = None) -> FaceAnalysis:
    """공통 분석 1회 생성 — 페르소나 무관 (v2 문서 §0)."""
    pts, warnings = extract_landmarks(image_bgr)
    features = compute_features(pts)

    samjeong = score_samjeong(features)
    ohaeng = score_ohaeng(features)

    return FaceAnalysis(
        analysis_id=analysis_id or uuid.uuid4().hex[:20],
        created_at=datetime.now(timezone.utc).isoformat(),
        raw_features={k: round(features[k], 4) for k in RAW_KEYS},
        buckets=bucketize(features, samjeong["dominant"]),
        ohaeng=ohaeng,
        samjeong=samjeong,
        type=resolve_type(ohaeng, samjeong),
        life_graph=compute_life_graph(ohaeng, samjeong),
        warnings=warnings,
    )
