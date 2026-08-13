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
from .pipeline import analyze_image
from .schemas import FaceAnalysis, PersonaInterpretation

app = FastAPI(title="픽팟 관상 분석", version="0.1.0")

DISCLAIMER = "본 결과는 오락 목적이며 과학적 근거가 없습니다."
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
FACES_DIR = Path(__file__).resolve().parent.parent / "tests" / "faces"
ALLOWED_MODELS = {"exaone3.5:2.4b", "exaone3.5:7.8b"}


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


@app.post("/api/interpret", response_model=PersonaInterpretation)
async def interpret(analysis_json: str = Form(...), persona: str = Form(...)):
    if persona not in ("KIND", "T", "ROAST"):
        raise HTTPException(400, "persona는 KIND | T | ROAST 중 하나여야 합니다.")
    analysis = json.loads(analysis_json)
    try:
        return llm.generate_persona(persona, analysis)
    except Exception as e:
        raise HTTPException(502, f"LLM 생성 실패: {e}")


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

    requested = [p.strip().upper() for p in personas.split(",") if p.strip()]
    interpretations = []
    for p in requested:
        if p not in ("KIND", "T", "ROAST"):
            raise HTTPException(400, f"알 수 없는 페르소나: {p}")
        interpretations.append(llm.generate_persona(p, analysis.model_dump(), model or None))
    return {"analysis": analysis, "interpretations": interpretations}


@app.get("/api/life-graph-svg")
def life_graph_svg(session_id: str, early: int, mid: int, late: int):
    svg = build_svg(session_id, {"early": early, "mid": mid, "late": late})
    return Response(content=svg, media_type="image/svg+xml")
