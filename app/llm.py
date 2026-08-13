"""LLM 생성 계층 — Ollama + EXAONE 3.5, JSON 스키마 문법 강제.

출력은 키오스크 소비 포맷(config/kiosk_json_update/KioskData_*.json)에 맞춘다:
- personaType: kind(다정다감) / factos(완전T) / spicy(독설가)
- reading.faceType.threeSections·fiveElements: 점수 + headline/description 해석
- 카테고리 5종(temperament/relationships/finances/executionAbility/health):
  headline / description / advice
- overallFortune, lifeFlow(early/middle/later), closingMessage

v1 설계 결정 유지:
- 구조는 JSON 스키마로 문법 강제, 분량은 프롬프트 숫자 지시로 평준화.
- 측정 수치 환각 방지: 입력에 없는 수치·퍼센트 인용 금지.
- claim(문체 없는 평문)은 검수용으로 별도 반환하고 키오스크 JSON에는 싣지 않는다.
"""
import json
import os
from datetime import datetime

import httpx

from . import persona as P
from .life_graph import _seeded_random

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("GWANSANG_MODEL", "exaone3.5:2.4b")
TIMEOUT = 300.0

_HD = {"type": "object",
       "properties": {"headline": {"type": "string"}, "description": {"type": "string"}},
       "required": ["headline", "description"]}
_SECTION = {"type": "object",
            "properties": {"claim": {"type": "string"}, "headline": {"type": "string"},
                           "description": {"type": "string"}, "advice": {"type": "string"}},
            "required": ["claim", "headline", "description", "advice"]}

_SCHEMA = {
    "type": "object",
    "properties": {
        "threeSections": _HD,
        "fiveElements": _HD,
        **{cat: _SECTION for cat in P.CATEGORIES},
        "overallFortune": _HD,
        "lifeFlow": {
            "type": "object",
            "properties": {
                "headline": {"type": "string"},
                "early": _HD, "middle": _HD, "later": _HD,
                "advice": {"type": "string"},
            },
            "required": ["headline", "early", "middle", "later", "advice"],
        },
        "closingMessage": {"type": "object",
                           "properties": {"description": {"type": "string"}},
                           "required": ["description"]},
    },
    "required": ["threeSections", "fiveElements", *P.CATEGORIES,
                 "overallFortune", "lifeFlow", "closingMessage"],
}

_ELEM_KO = {"wood": "목(木)", "fire": "화(火)", "earth": "토(土)", "metal": "금(金)", "water": "수(水)"}
_DOM_KO = {"upper": "상정", "mid": "중정", "lower": "하정", "balanced": "삼정 균형"}


def _graph_phase_desc(score: int) -> str:
    if score >= 75:
        flow = "좋은 흐름"
    elif score >= 60:
        flow = "무난한 흐름"
    else:
        flow = "주의할 흐름"
    return f"{score}점 ({flow})"


def _build_prompt(persona: str, analysis: dict) -> str:
    oh, sj, lg = analysis["ohaeng"], analysis["samjeong"], analysis["life_graph"]
    lines = [
        "너는 관상 풀이 작가다. 아래 실측 데이터만 근거로 관상 해석 JSON을 작성한다.",
        "",
        "[절대 규칙]",
        "- 입력에 없는 수치·퍼센트를 지어내지 마라. 제공된 라벨과 점수만 인용한다.",
        "- 한국어만 사용한다. 영어 단어를 섞지 마라.",
        "- headline은 10~25자의 재치 있는 비유 카피 (예: '내 사람에게만 열리는 시크릿 VIP 라운지').",
        "- description은 2~3문장, 90~160자. advice는 1~2문장.",
        "- claim은 문체 없는 건조한 평문 1문장 (검수용).",
        f"- {P.COMMON_TONE}",
        "",
        f"[페르소나] {P.PERSONA_KO[persona]}",
        f"[문체] {P.PERSONA_STYLE[persona]}",
        "",
        "[분석 대상]",
        f"- 유형: {analysis['type']['name']} — {analysis['type']['tagline']}",
        f"- 오행: 주형 {_ELEM_KO[oh['main']]} / 보조 {_ELEM_KO[oh['sub']]}",
        f"- 삼정: 상정 {sj['upper']} / 중정 {sj['mid']} / 하정 {sj['lower']} (지배: {_DOM_KO[sj['dominant']]})",
        "",
        "[블록별 과제]",
        f"- threeSections: 삼정 수치가 말하는 기질 구조를 해석 (지배 영역 {_DOM_KO[sj['dominant']]} 중심).",
        f"- fiveElements: 주형 {_ELEM_KO[oh['main']]}과 보조 {_ELEM_KO[oh['sub']]}의 조합이 드러나는 방식을 해석.",
    ]
    for cat in P.CATEGORIES:
        q = P.QUESTION_MATRIX[(persona, cat)]
        ev = P.evidence_value(P.PRIMARY_EVIDENCE[(persona, cat)], analysis)
        lines.append(f"- {cat}({P.CATEGORY_KO[cat]}): 질문 「{q}」 / 근거 「{ev}」 — 근거를 문장 속에 자연스럽게 녹일 것.")
    lines += [
        "- overallFortune(종합운): 위 해석 전체를 관통하는 가장 지배적인 패턴 하나를 요약.",
        "",
        "[lifeFlow 인생그래프]",
        # 흐름 판정은 코드에서 확정해 주입 — 모델의 상대 비교 왜곡 방지
        f"- early(초년): {_graph_phase_desc(lg['early'])}",
        f"- middle(중년): {_graph_phase_desc(lg['mid'])}",
        f"- later(말년): {_graph_phase_desc(lg['late'])}",
        f"- 질문: {P.GRAPH_QUESTION[persona]}",
        "- 각 시기는 위 흐름 판정과 모순되게 서술하지 마라.",
        "",
        "[closingMessage 마지막 한 줄]",
        f"- {P.FINAL_LINE_RULE[persona]}. 새 분석을 만들지 말고 위 해석에서 압축할 것. 40자 이내.",
    ]
    return "\n".join(lines)


def generate_reading(persona: str, analysis: dict, model: str | None = None) -> dict:
    """페르소나 1개의 해석 생성 → (키오스크 reading 블록, 검수용 claims)."""
    payload = {
        "model": model or MODEL,
        "messages": [{"role": "user", "content": _build_prompt(persona, analysis)}],
        "stream": False,
        "format": _SCHEMA,
        "options": {"temperature": 0.7, "num_ctx": 4096},
    }
    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.post(f"{OLLAMA_URL}/api/chat", json=payload)
        resp.raise_for_status()
        out = json.loads(resp.json()["message"]["content"])

    claims = {cat: out[cat].pop("claim", "") for cat in P.CATEGORIES}
    return out, claims


def _print_code(analysis_id: str, persona: str) -> str:
    return f"{int(_seeded_random(analysis_id, f'print:{persona}') * 100000):05d}"


def assemble_kiosk_data(persona: str, analysis: dict, out: dict,
                        session_id: str | None = None) -> dict:
    """LLM 출력 + 공통 분석 → 키오스크 소비 JSON (KioskData_*.json 스키마)."""
    sj, oh = analysis["samjeong"], analysis["ohaeng"]
    now = datetime.now().astimezone()
    dominant_map = {"upper": "upper", "mid": "middle", "lower": "lower", "balanced": "balanced"}
    return {
        "sessionId": session_id or analysis["analysis_id"],
        "createdAt": now.isoformat(timespec="milliseconds"),
        "artifactDate": now.date().isoformat(),
        "personaType": P.PERSONA_KIOSK[persona],
        "printCode": _print_code(analysis["analysis_id"], persona),
        "status": "completed",
        "reading": {
            "faceType": {
                "name": analysis["type"]["name"],
                "description": analysis["type"]["tagline"],
                "threeSections": {
                    "scores": {"upper": sj["upper"], "middle": sj["mid"], "lower": sj["lower"]},
                    "primary": dominant_map[sj["dominant"]],
                    **out["threeSections"],
                },
                "fiveElements": {
                    "scores": {e: oh[e] for e in ("wood", "fire", "earth", "metal", "water")},
                    "primary": oh["main"],
                    "secondary": oh["sub"],
                    **out["fiveElements"],
                },
            },
            **{cat: out[cat] for cat in P.CATEGORIES},
            "overallFortune": out["overallFortune"],
            "lifeFlow": {
                "headline": out["lifeFlow"]["headline"],
                "stages": {
                    "early": out["lifeFlow"]["early"],
                    "middle": out["lifeFlow"]["middle"],
                    "later": out["lifeFlow"]["later"],
                },
                "advice": out["lifeFlow"]["advice"],
            },
            "closingMessage": out["closingMessage"],
        },
    }


def generate_kiosk_data(persona: str, analysis: dict, model: str | None = None,
                        session_id: str | None = None) -> tuple[dict, dict]:
    """편의 함수: 생성 + 조립. (kiosk_data, claims) 반환."""
    out, claims = generate_reading(persona, analysis, model)
    return assemble_kiosk_data(persona, analysis, out, session_id), claims


def check_health() -> bool:
    try:
        with httpx.Client(timeout=3.0) as client:
            return client.get(f"{OLLAMA_URL}/api/tags").status_code == 200
    except httpx.HTTPError:
        return False
