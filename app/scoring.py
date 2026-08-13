"""오행·삼정 점수화 및 20유형 판정 — 미로 v2 문서 §1 기준.

- 삼정: 실측 평균 기준선 + 표준편차 z-점수 정규화 (v1 설계 결정 #3).
  ZONE_BASELINE은 시작값이며 테스트 촬영 100건으로 재캘리브레이션 대상.
- DOMINANT: range(최고-최저) > 8 이면 최고점 영역, 아니면 balanced.
  동점 우선순위 중정 > 상정 > 하정. 임계값 8도 실측 튜닝 대상 (목표 균형형 배출 15~20%).
- 오행: 특징 z-점수 가중합 휴리스틱. 오락 서비스 기준의 결정론적 룰.
"""
import numpy as np

# (평균, 표준편차) — 테스트 5장 실측 평균 기준 (상정은 헤어라인 미인식으로 이론값보다 낮음)
# ⚠ 표본 5장(연예인 정면 사진). 현장 테스트 촬영 100건으로 재캘리브레이션 필수.
ZONE_BASELINE = [(0.203, 0.030), (0.405, 0.025), (0.392, 0.036)]  # 상, 중, 하

# 오행 채점용 특징 기준선 (평균, 표준편차) — 테스트 5장 실측 기반
_FEATURE_BASELINE = {
    "face_ratio": (1.186, 0.06),
    "jaw_width": (0.881, 0.025),
    "jaw_angle": (138.5, 5.0),
    "eye_height": (0.378, 0.04),
    "eye_tilt": (6.2, 2.5),
    "nose_length": (0.303, 0.02),
    "nose_width": (0.249, 0.015),
    "lip_thickness": (0.103, 0.010),
    "mouth_width": (0.367, 0.025),
    "cheekbone_width": (0.844, 0.03),
    "symmetry": (0.150, 0.060),
    "brow_angle": (4.2, 3.8),
}

_Z_CLIP = 2.5  # 개별 특징의 극단값이 오행 점수를 붕괴시키지 않도록 클리핑

# 오행별 특징 가중치: z-점수 × weight 합산 → 50 + 12·(가중 z)
_OHAENG_WEIGHTS = {
    "wood":  {"face_ratio": 1.0, "nose_length": 0.7, "jaw_width": -0.5, "eye_height": 0.2},      # 갸름·긴 얼굴
    "fire":  {"eye_tilt": 0.9, "jaw_width": -0.6, "brow_angle": 0.5, "mouth_width": 0.3},         # 상향·뾰족
    "earth": {"jaw_width": 0.8, "lip_thickness": 0.7, "face_ratio": -0.5, "nose_width": 0.4},     # 두툼·안정
    "metal": {"jaw_angle": -0.9, "symmetry": -0.7, "face_ratio": 0.2, "brow_angle": 0.4},         # 각·정돈
    "water": {"eye_height": 0.8, "jaw_angle": 0.6, "face_ratio": -0.4, "mouth_width": 0.3},       # 둥글·부드러움
}

_ELEMENTS = ["wood", "fire", "earth", "metal", "water"]
# v2 문서 시작값 8 → 테스트 5장 대조 후 10으로 조정 (균형형 배출 1/5 = 20%, 목표 구간)
DOMINANT_RANGE_THRESHOLD = 10


def _clamp100(v: float) -> int:
    return int(round(max(0, min(100, v))))


def score_samjeong(features: dict[str, float]) -> dict:
    zones = [features["upper_zone"], features["mid_zone"], features["lower_zone"]]
    scores = []
    for v, (mean, std) in zip(zones, ZONE_BASELINE):
        z = max(-_Z_CLIP, min(_Z_CLIP, (v - mean) / std))
        scores.append(_clamp100(72 + z * 11))  # 평균 얼굴 → 72점 중심, ±2.5σ → 44~100
    upper, mid, lower = scores

    rng = max(scores) - min(scores)
    if rng <= DOMINANT_RANGE_THRESHOLD:
        dominant = "balanced"
    else:
        # 동점 우선순위: 중정 > 상정 > 하정
        best = max(scores)
        dominant = ("mid", "upper", "lower")[[mid, upper, lower].index(best)]
    return {"upper": upper, "mid": mid, "lower": lower, "dominant": dominant}


def score_ohaeng(features: dict[str, float]) -> dict:
    z = {}
    for key, (mean, std) in _FEATURE_BASELINE.items():
        z[key] = max(-_Z_CLIP, min(_Z_CLIP, (features[key] - mean) / std))

    scores = {}
    for elem, weights in _OHAENG_WEIGHTS.items():
        total_w = sum(abs(w) for w in weights.values())
        weighted = sum(z[k] * w for k, w in weights.items()) / total_w
        scores[elem] = _clamp100(72 + weighted * 12)

    ranked = sorted(_ELEMENTS, key=lambda e: scores[e], reverse=True)
    return {**scores, "main": ranked[0], "sub": ranked[1]}


def compute_life_graph(ohaeng: dict, samjeong: dict) -> dict:
    """초/중/말년 수치 — 삼정을 골격으로 오행 주형이 변주 (내부 룰셋)."""
    base = {"early": samjeong["upper"], "mid": samjeong["mid"], "late": samjeong["lower"]}
    # 오행 주형별 보정: 기운이 실리는 시기가 다르다는 통념 반영
    modifier = {
        "wood":  {"early": +4, "mid": +2, "late": 0},   # 성장·기획 — 이른 상승
        "fire":  {"early": +2, "mid": +5, "late": -2},  # 확산 — 중년 정점
        "earth": {"early": 0,  "mid": +2, "late": +4},  # 축적 — 후반 안정
        "metal": {"early": -2, "mid": +4, "late": +3},  # 결실 — 중후반
        "water": {"early": +3, "mid": 0,  "late": +4},  # 유연 — 양끝
    }[ohaeng["main"]]
    return {k: _clamp100(base[k] + modifier[k]) for k in base}
