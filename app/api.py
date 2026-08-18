"""외부 앱 통합용 진입점.

FastAPI 없이 이 모듈만 import 하면 파이프라인 전체를 쓸 수 있다.

    from app.api import analyze_photo
    result = analyze_photo("face.jpg", personas=["kind", "spicy"])
    result["readings"]["kind"]      # 키오스크 소비 JSON (KioskData_kind.json 구조)
    result["analysis"]              # 공통 분석 (유형·오행·삼정·인생그래프)

이미지는 파일 경로 / bytes / numpy 배열(BGR) 모두 받는다.
LLM 없이 유형 판정만 필요하면 analyze_only()를 쓴다 (0.05초, Ollama 불필요).
"""
from pathlib import Path

import cv2
import numpy as np

from . import llm
from .landmarks import FaceDetectionError  # noqa: F401  (호출자가 잡을 예외)
from .life_graph import build_svg
from .persona import PERSONA_FROM_KIOSK, PERSONA_KIOSK
from .pipeline import analyze_image
from .schemas import FaceAnalysis

DISCLAIMER = "본 결과는 오락 목적이며 과학적 근거가 없습니다."


def _to_bgr(image) -> np.ndarray:
    """경로 / bytes / ndarray → OpenCV BGR 배열."""
    if isinstance(image, np.ndarray):
        return image
    if isinstance(image, (bytes, bytearray)):
        img = cv2.imdecode(np.frombuffer(image, dtype=np.uint8), cv2.IMREAD_COLOR)
    elif isinstance(image, (str, Path)):
        img = cv2.imread(str(image))
    else:
        raise TypeError(f"지원하지 않는 이미지 타입: {type(image)}")
    if img is None:
        raise ValueError("이미지를 열 수 없습니다.")
    return img


def _normalize(persona: str) -> str:
    """kind/factos/spicy 또는 KIND/T/ROAST 모두 허용 → 내부 코드."""
    if persona.upper() in PERSONA_KIOSK:
        return persona.upper()
    if persona.lower() in PERSONA_FROM_KIOSK:
        return PERSONA_FROM_KIOSK[persona.lower()]
    raise ValueError(f"알 수 없는 페르소나: {persona} (kind|factos|spicy)")


def analyze_only(image, analysis_id: str | None = None) -> FaceAnalysis:
    """LLM 없이 얼굴 분석만 — 유형·오행·삼정·인생그래프 수치. 약 0.05초.

    얼굴이 0개 또는 2개 이상이면 FaceDetectionError.
    """
    result = analyze_image(_to_bgr(image), analysis_id)
    result.warnings.append(DISCLAIMER)
    return result


def analyze_photo(image, personas=("kind",), model: str | None = None,
                  session_id: str | None = None, with_claims: bool = False) -> dict:
    """사진 1장 → 공통 분석 + 페르소나별 해석.

    personas: kind(다정다감) / factos(완전T) / spicy(독설가)
    model:    None이면 환경변수 GWANSANG_MODEL 또는 기본값
    반환:     {"analysis": {...}, "readings": {"kind": {키오스크 JSON}, ...}}
              with_claims=True면 "claims"(문체 없는 평문, 검수용)도 포함
    """
    analysis = analyze_only(image)
    data = analysis.model_dump()

    readings, claims = {}, {}
    for p in personas:
        code = _normalize(p)
        kiosk, claim = llm.generate_kiosk_data(code, data, model, session_id)
        readings[PERSONA_KIOSK[code]] = kiosk
        claims[PERSONA_KIOSK[code]] = claim

    out = {"analysis": data, "readings": readings}
    if with_claims:
        out["claims"] = claims
    return out


def life_graph_svg(analysis: dict | FaceAnalysis) -> str:
    """인생그래프 SVG 문자열 (영수증·포토카드 출력에 그대로 재사용)."""
    data = analysis.model_dump() if isinstance(analysis, FaceAnalysis) else analysis
    return build_svg(data["analysis_id"], data["life_graph"])


def check_llm() -> bool:
    """Ollama 응답 여부 — 앱 기동 시 헬스체크용."""
    return llm.check_health()
