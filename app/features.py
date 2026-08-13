"""478 랜드마크 → 수치 특징 추출.

반환 dict은 두 그룹:
- RawFeatures 17개 (스키마 노출, 미로 v2 문서 §10)
- 버킷 전용 보조값 (brow_arch, eye_gap, lip_thickness, lip_ratio, mouth_corner,
  jaw_angle, mouth_size) — celeb_comparison.html의 18특징 라벨 재현용

랜드마크 인덱스는 MediaPipe FaceMesh 표준 토폴로지 기준.
정밀 튜닝 대상은 config/buckets.yaml 임계값이며, 인덱스 자체는 근사로 시작한다.
"""
import numpy as np

# 주요 인덱스
TOP, CHIN = 10, 152
NASION, SUBNASALE, UPPER_LIP_TOP = 168, 2, 0
L_FACE, R_FACE = 234, 454           # 광대 부근 얼굴 외곽
L_JAW, R_JAW = 58, 288              # 하악각(고니온) 근사
L_EYE_OUT, L_EYE_IN, L_EYE_UP, L_EYE_DN = 33, 133, 159, 145
R_EYE_IN, R_EYE_OUT, R_EYE_UP, R_EYE_DN = 362, 263, 386, 374
L_BROW_IN, L_BROW_PEAK, L_BROW_OUT = 55, 105, 70
R_BROW_IN, R_BROW_PEAK, R_BROW_OUT = 285, 334, 300
L_NOSE_ALA, R_NOSE_ALA = 64, 294
L_FOREHEAD, R_FOREHEAD = 54, 284    # 이마 측면(관자놀이 위) 외곽
L_MOUTH, R_MOUTH = 61, 291
LIP_UP_IN, LIP_DN_IN, LIP_DN_BOT = 13, 14, 17

# 좌우 대칭 쌍 (symmetry 계산용, 대표 부위만)
_SYM_PAIRS = [
    (L_EYE_OUT, R_EYE_OUT), (L_EYE_IN, R_EYE_IN), (L_BROW_PEAK, R_BROW_PEAK),
    (L_NOSE_ALA, R_NOSE_ALA), (L_MOUTH, R_MOUTH), (L_JAW, R_JAW), (L_FACE, R_FACE),
]


def _d(pts, a, b):
    return float(np.linalg.norm(pts[a] - pts[b]))


def compute_features(pts: np.ndarray) -> dict[str, float]:
    face_h = abs(pts[CHIN][1] - pts[TOP][1])
    face_w = _d(pts, L_FACE, R_FACE)

    brow_y = float(np.mean([pts[i][1] for i in (L_BROW_IN, L_BROW_PEAK, R_BROW_IN, R_BROW_PEAK)]))
    upper = abs(brow_y - pts[TOP][1])
    mid = abs(pts[SUBNASALE][1] - brow_y)
    lower = abs(pts[CHIN][1] - pts[SUBNASALE][1])
    zone_total = upper + mid + lower

    # 눈
    eye_w = (_d(pts, L_EYE_OUT, L_EYE_IN) + _d(pts, R_EYE_IN, R_EYE_OUT)) / 2
    eye_h = (_d(pts, L_EYE_UP, L_EYE_DN) + _d(pts, R_EYE_UP, R_EYE_DN)) / 2
    # 눈꼬리 각도: 코너(외측)가 내측보다 위면 양수 (이미지 y축은 아래로 증가)
    l_tilt = np.degrees(np.arctan2(pts[L_EYE_IN][1] - pts[L_EYE_OUT][1], _d(pts, L_EYE_OUT, L_EYE_IN)))
    r_tilt = np.degrees(np.arctan2(pts[R_EYE_IN][1] - pts[R_EYE_OUT][1], _d(pts, R_EYE_IN, R_EYE_OUT)))
    eye_tilt = float((l_tilt + r_tilt) / 2)

    # 눈썹: 각도(내→외 상승이 양수) / 아치(피크가 내외 평균보다 위)
    l_ba = np.degrees(np.arctan2(pts[L_BROW_IN][1] - pts[L_BROW_OUT][1], _d(pts, L_BROW_OUT, L_BROW_IN)))
    r_ba = np.degrees(np.arctan2(pts[R_BROW_IN][1] - pts[R_BROW_OUT][1], _d(pts, R_BROW_IN, R_BROW_OUT)))
    brow_angle = float((l_ba + r_ba) / 2)
    l_arch = (pts[L_BROW_IN][1] + pts[L_BROW_OUT][1]) / 2 - pts[L_BROW_PEAK][1]
    r_arch = (pts[R_BROW_IN][1] + pts[R_BROW_OUT][1]) / 2 - pts[R_BROW_PEAK][1]
    brow_arch = float((l_arch + r_arch) / 2 / eye_w)

    # 입술
    lip_upper = abs(pts[UPPER_LIP_TOP][1] - pts[LIP_UP_IN][1])
    lip_lower = abs(pts[LIP_DN_BOT][1] - pts[LIP_DN_IN][1])
    lip_center_y = (pts[LIP_UP_IN][1] + pts[LIP_DN_IN][1]) / 2
    mouth_corner = float((lip_center_y - (pts[L_MOUTH][1] + pts[R_MOUTH][1]) / 2) / eye_w)

    # 턱선 각도: 고니온에서 (귀쪽 수직) vs (턱끝 방향) 사잇각 평균 — 클수록 완만
    jaw_angle = float((_angle_at(pts, L_FACE, L_JAW, CHIN) + _angle_at(pts, R_FACE, R_JAW, CHIN)) / 2)

    # 좌우 균형: 얼굴 중심축 대비 대칭쌍 x편차 평균 (0에 가까울수록 대칭)
    cx = (pts[L_FACE][0] + pts[R_FACE][0]) / 2
    asym = float(np.mean([abs((cx - pts[a][0]) - (pts[b][0] - cx)) for a, b in _SYM_PAIRS]) / face_w)

    return {
        # === RawFeatures 17 ===
        "face_ratio": face_h / face_w,
        "upper_zone": upper / zone_total,
        "mid_zone": mid / zone_total,
        "lower_zone": lower / zone_total,
        "brow_angle": brow_angle,
        "glabella_width": _d(pts, L_BROW_IN, R_BROW_IN) / face_w,
        "eye_width": eye_w / face_w,
        "eye_height": eye_h / eye_w,
        "eye_tilt": eye_tilt,
        "cheekbone_width": face_w / face_h,
        "nose_length": abs(pts[SUBNASALE][1] - pts[NASION][1]) / face_h,
        "nose_width": _d(pts, L_NOSE_ALA, R_NOSE_ALA) / face_w,
        "philtrum": abs(pts[UPPER_LIP_TOP][1] - pts[SUBNASALE][1]) / face_h,
        "mouth_width": _d(pts, L_MOUTH, R_MOUTH) / face_w,
        "jaw_length": abs(pts[CHIN][1] - pts[LIP_DN_BOT][1]) / face_h,
        "jaw_width": _d(pts, L_JAW, R_JAW) / face_w,
        "symmetry": asym,
        # === 버킷 보조값 ===
        "forehead_width": _d(pts, L_FOREHEAD, R_FOREHEAD) / face_w,
        "eye_gap": _d(pts, L_EYE_IN, R_EYE_IN) / eye_w,
        "brow_arch": brow_arch,
        "lip_thickness": (lip_upper + lip_lower) / face_h,
        "lip_ratio": lip_upper / max(lip_lower, 1e-6),
        "mouth_corner": mouth_corner,
        "jaw_angle": jaw_angle,
    }


def _angle_at(pts, a, vertex, b) -> float:
    v1, v2 = pts[a] - pts[vertex], pts[b] - pts[vertex]
    cos = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-9)
    return float(np.degrees(np.arccos(np.clip(cos, -1, 1))))
