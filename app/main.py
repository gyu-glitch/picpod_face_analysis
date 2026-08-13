"""관상 분석 API — FastAPI.

POST /api/analyze          이미지 → FaceAnalysis (공통 분석)
POST /api/interpret        FaceAnalysis + 페르소나 → PersonaInterpretation (LLM)
POST /api/analyze-full     이미지 → 공통 분석 + 페르소나 해석 일괄 (편의용)
GET  /api/life-graph-svg   sessionId + 삼정 점수 → SVG
GET  /health
"""
import json
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response

from . import llm
from .landmarks import FaceDetectionError
from .life_graph import build_svg
from .persona import PERSONA_FROM_KIOSK, PERSONA_KIOSK
from .pipeline import analyze_image
from .schemas import FaceAnalysis

app = FastAPI(title="픽팟 관상 분석", version="0.1.0")

DISCLAIMER = "본 결과는 오락 목적이며 과학적 근거가 없습니다."
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
FACES_DIR = Path(__file__).resolve().parent.parent / "tests" / "faces"
RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
ALLOWED_MODELS = {"exaone3.5:2.4b", "exaone3.5:7.8b"}


def _save_results(analysis: FaceAnalysis, interpretations: list[dict]) -> str:
    """분석 결과를 results/에 영속화 — 클라이언트 수신기가 폴링해 가져간다."""
    from datetime import datetime
    batch = f"{datetime.now():%Y%m%d_%H%M%S}_{analysis.analysis_id[:8]}"
    out = RESULTS_DIR / batch
    out.mkdir(parents=True, exist_ok=True)
    (out / "analysis.json").write_text(
        json.dumps(analysis.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
    for kiosk in interpretations:
        (out / f"KioskData_{kiosk['personaType']}.json").write_text(
            json.dumps(kiosk, ensure_ascii=False, indent=2), encoding="utf-8")
    return batch


def _decode_upload(data: bytes) -> np.ndarray:
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "이미지를 해석할 수 없습니다.")
    return img


@app.get("/health")
def health():
    return {"status": "ok", "ollama": llm.check_health(), "model": llm.MODEL}


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/test-faces")
def list_test_faces():
    if not FACES_DIR.exists():
        return []
    return sorted(p.name for p in FACES_DIR.glob("*.jpg"))


@app.get("/api/test-faces/{name}")
def get_test_face(name: str):
    path = (FACES_DIR / name).resolve()
    if not path.is_file() or path.parent != FACES_DIR.resolve():
        raise HTTPException(404, "샘플 없음")
    return FileResponse(path)


@app.post("/api/analyze", response_model=FaceAnalysis)
async def analyze(file: UploadFile = File(...)):
    img = _decode_upload(await file.read())
    try:
        analysis = analyze_image(img)
    except FaceDetectionError as e:
        raise HTTPException(422, str(e))
    analysis.warnings.append(DISCLAIMER)
    return analysis


def _normalize_persona(p: str) -> str:
    """KIND/T/ROAST(내부) 또는 kind/factos/spicy(키오스크) 표기 모두 허용."""
    p = p.strip()
    if p.upper() in PERSONA_KIOSK:
        return p.upper()
    if p.lower() in PERSONA_FROM_KIOSK:
        return PERSONA_FROM_KIOSK[p.lower()]
    raise HTTPException(400, f"알 수 없는 페르소나: {p}")


@app.post("/api/interpret")
async def interpret(
    analysis_json: str = Form(...),
    persona: str = Form(...),
    model: str = Form(""),
    session_id: str = Form(""),
):
    """공통 분석 JSON + 페르소나 → 키오스크 소비 포맷(KioskData_*.json)."""
    p = _normalize_persona(persona)
    if model and model not in ALLOWED_MODELS:
        raise HTTPException(400, f"지원하지 않는 모델: {model}")
    analysis = json.loads(analysis_json)
    try:
        kiosk, claims = llm.generate_kiosk_data(p, analysis, model or None, session_id or None)
    except Exception as e:
        raise HTTPException(502, f"LLM 생성 실패: {e}")
    return {"kiosk_data": kiosk, "claims": claims}


@app.post("/api/analyze-full")
async def analyze_full(
    file: UploadFile | None = File(None),
    sample: str = Form(""),
    personas: str = Form("KIND"),
    model: str = Form(""),
):
    if file is not None:
        img = _decode_upload(await file.read())
    elif sample:
        path = (FACES_DIR / sample).resolve()
        if not path.is_file() or path.parent != FACES_DIR.resolve():
            raise HTTPException(404, "샘플 없음")
        img = cv2.imread(str(path))
    else:
        raise HTTPException(400, "file 또는 sample 중 하나가 필요합니다.")

    if model and model not in ALLOWED_MODELS:
        raise HTTPException(400, f"지원하지 않는 모델: {model}")

    try:
        analysis = analyze_image(img)
    except FaceDetectionError as e:
        raise HTTPException(422, str(e))
    analysis.warnings.append(DISCLAIMER)

    requested = [_normalize_persona(p) for p in personas.split(",") if p.strip()]
    interpretations, claims = [], {}
    for p in requested:
        kiosk, c = llm.generate_kiosk_data(p, analysis.model_dump(), model or None)
        interpretations.append(kiosk)
        claims[PERSONA_KIOSK[p]] = c
    batch = _save_results(analysis, interpretations)
    return {"analysis": analysis, "interpretations": interpretations,
            "claims": claims, "batch": batch}


@app.get("/api/results")
def list_results(after: str = ""):
    """after(배치명) 이후 생성된 결과 배치 목록 — 클라이언트 수신기 폴링용."""
    if not RESULTS_DIR.exists():
        return []
    batches = sorted(d.name for d in RESULTS_DIR.iterdir() if d.is_dir())
    new = [b for b in batches if b > after]
    return [{"batch": b, "files": sorted(f.name for f in (RESULTS_DIR / b).glob("*.json"))}
            for b in new]


@app.get("/api/results/{batch}/{filename}")
def get_result_file(batch: str, filename: str):
    path = (RESULTS_DIR / batch / filename).resolve()
    if not path.is_file() or RESULTS_DIR.resolve() not in path.parents:
        raise HTTPException(404, "파일 없음")
    return FileResponse(path, media_type="application/json")


@app.get("/api/life-graph-svg")
def life_graph_svg(session_id: str, early: int, mid: int, late: int):
    svg = build_svg(session_id, {"early": early, "mid": mid, "late": late})
    return Response(content=svg, media_type="image/svg+xml")
