"""관상 분석 결과 데이터 구조 — 미로 '관상중독 — 결과 산출 구조' §10 기준."""
from typing import Literal, Optional
from pydantic import BaseModel, Field


class RawFeatures(BaseModel):
    face_ratio: float
    upper_zone: float
    mid_zone: float
    lower_zone: float
    brow_angle: float
    glabella_width: float
    eye_width: float
    eye_height: float
    eye_tilt: float
    cheekbone_width: float
    nose_length: float
    nose_width: float
    philtrum: float
    mouth_width: float
    jaw_length: float
    jaw_width: float
    symmetry: float


class Ohaeng(BaseModel):
    wood: int
    fire: int
    earth: int
    metal: int
    water: int
    main: Literal["wood", "fire", "earth", "metal", "water"]
    sub: Literal["wood", "fire", "earth", "metal", "water"]


class Samjeong(BaseModel):
    upper: int
    mid: int
    lower: int
    dominant: Literal["upper", "mid", "lower", "balanced"]


class TypeInfo(BaseModel):
    code: str  # {WOOD|FIRE|EARTH|METAL|WATER}_{UPPER|MID|LOWER|BALANCED}
    name: str
    tagline: str
    subtext: str


class LifeGraph(BaseModel):
    early: int
    mid: int
    late: int


class FaceAnalysis(BaseModel):
    """사람에 귀속 / 1회 생성 / 페르소나 무관."""
    analysis_id: str
    created_at: str
    raw_features: RawFeatures
    buckets: dict[str, str]  # 특징 → 한국어 라벨 (18개, 프롬프트/검수용)
    ohaeng: Ohaeng
    samjeong: Samjeong
    type: TypeInfo
    life_graph: LifeGraph
    warnings: list[str] = Field(default_factory=list)


class Evidence(BaseModel):
    primary: str
    secondary: Optional[str] = None
    style: Literal["LIGHT", "MEDIUM", "STRONG"]


class Section(BaseModel):
    category: Literal["temperament", "relationship", "money", "execution", "health"]
    question_key: str
    evidence: Evidence
    claim: str    # 문체 적용 전 평문 (중복 검수용)
    advice: str   # 문체 적용 전 평문
    headline: str  # 문체 적용 후
    body: str      # 문체 적용 후


class GraphPhase(BaseModel):
    headline: str
    body: str


class LifeGraphReading(BaseModel):
    summary: str
    early: GraphPhase
    mid: GraphPhase
    late: GraphPhase
    advice: str


class PersonaInterpretation(BaseModel):
    """analysis_id에 종속 / 페르소나별 최대 3개."""
    analysis_id: str
    persona: Literal["KIND", "T", "ROAST"]
    sections: list[Section]
    life_graph_reading: LifeGraphReading
    final_line: str
