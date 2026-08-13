"""수치 특징 → 한국어 라벨 버킷화 (buckets.yaml 기반)."""
from pathlib import Path
import yaml

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "buckets.yaml"
_config: dict | None = None


def _load() -> dict:
    global _config
    if _config is None:
        _config = yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8"))
    return _config


_SAMJEONG_LABEL = {
    "upper": "상정(이마 부위)이 발달함",
    "mid": "중정(눈~코 부위)이 발달함",
    "lower": "하정(입~턱 부위)이 발달함",
    "balanced": "상정·중정·하정이 고르게 균형 잡힘",
}


def bucketize(features: dict[str, float], samjeong_dominant: str) -> dict[str, str]:
    """18개 표시 특징의 {표시명: 라벨} dict 반환.

    삼정 비율 라벨은 scoring.score_samjeong의 dominant 판정을 그대로 사용해
    점수와 라벨이 어긋나지 않게 한다.
    """
    cfg = _load()
    out = {"삼정 비율": _SAMJEONG_LABEL[samjeong_dominant]}
    for key, spec in cfg.items():
        if key not in features:
            continue
        lo, hi = spec["thresholds"]
        v = features[key]
        idx = 0 if v < lo else (1 if v < hi else 2)
        out[spec["display"]] = spec["labels"][idx]
    return out
