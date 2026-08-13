"""LLM 생성 계층 — Ollama + EXAONE 3.5, JSON 스키마 문법 강제.

v1 설계 결정 재적용:
- 출력 구조(섹션 5개, 카테고리 순서·값)는 스키마 prefixItems+const로 문법 강제.
- 분량은 프롬프트 숫자 지시("2~3문장, 90~140자")로 평준화 — minLength 강제 금지.
- 측정 수치 환각 방지: 입력에 없는 퍼센트/수치를 지어내지 말라고 명시
  (celeb_comparison 리포트에서 2.4B가 '중정 42%' 등을 환각한 이력).
"""
import json
import os

import httpx

from . import persona as P

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("GWANSANG_MODEL", "exaone3.5:2.4b")
TIMEOUT = 180.0


def _section_schema(persona: str) -> dict:
    """섹션 5개를 카테고리 키 고정 객체로 강제하는 JSON 스키마.

    v1은 prefixItems+const를 썼으나 Ollama 스키마 변환기가 `items: false`를
    지원하지 않아, 동일한 효과(개수·순서·중복의 문법적 차단)를
    required 5키 객체로 구현한다. 배열 변환은 generate_persona에서 수행.
    """
    section = {
        "type": "object",
        "properties": {
            "claim": {"type": "string"},
            "advice": {"type": "string"},
            "headline": {"type": "string"},
            "body": {"type": "string"},
        },
        "required": ["claim", "advice", "headline", "body"],
    }
    phase = {
        "type": "object",
        "properties": {"headline": {"type": "string"}, "body": {"type": "string"}},
        "required": ["headline", "body"],
    }
    return {
        "type": "object",
        "properties": {
            "sections": {
                "type": "object",
                "properties": {cat: section for cat in P.CATEGORIES},
                "required": list(P.CATEGORIES),
            },
            "life_graph_reading": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "early": phase, "mid": phase, "late": phase,
                    "advice": {"type": "string"},
                },
                "required": ["summary", "early", "mid", "late", "advice"],
            },
            "final_line": {"type": "string"},
        },
        "required": ["sections", "life_graph_reading", "final_line"],
    }


def _graph_phase_desc(score: int) -> str:
    if score >= 75:
        flow = "좋은 흐름"
    elif score >= 60:
        flow = "무난한 흐름"
    else:
        flow = "주의할 흐름"
    return f"{score}점 ({flow})"


def _build_prompt(persona: str, analysis: dict) -> str:
    lines = [
        "너는 관상 풀이 작가다. 아래 실측 데이터만 근거로 관상 해석을 작성한다.",
        "",
        "[절대 규칙]",
        "- 입력에 없는 수치·퍼센트를 지어내지 마라. 아래 제공된 라벨과 점수만 인용한다.",
        "- 한국어만 사용한다. 영어 단어를 섞지 마라.",
        "- 각 섹션의 body는 반드시 2~3문장, 90~140자.",
        "- claim/advice는 문체 없는 평문 1문장, headline은 12자 이내, body는 문체 적용문.",
        f"- {P.COMMON_TONE}",
        "",
        f"[페르소나] {P.PERSONA_KO[persona]}",
        f"[문체] {P.PERSONA_STYLE[persona]}",
        "",
        "[분석 대상]",
        f"- 유형: {analysis['type']['name']} ({analysis['type']['code']})",
        f"- 오행: 주형 {analysis['ohaeng']['main']} / 보조 {analysis['ohaeng']['sub']}",
        f"- 삼정: 상정 {analysis['samjeong']['upper']} / 중정 {analysis['samjeong']['mid']}"
        f" / 하정 {analysis['samjeong']['lower']} (지배: {analysis['samjeong']['dominant']})",
        "",
        "[섹션별 과제 — 순서 고정, 각 섹션은 지정된 근거만 사용]",
    ]
    for cat in P.CATEGORIES:
        q = P.QUESTION_MATRIX[(persona, cat)]
        ev_key = P.PRIMARY_EVIDENCE[(persona, cat)]
        ev = P.evidence_value(ev_key, analysis)
        lines.append(f"- {P.CATEGORY_KO[cat]}({cat}): 질문 「{q}」 / 근거 「{ev}」")
    lines += [
        "",
        "[인생그래프]",
        # 흐름 판정은 코드에서 확정해 주입 — 모델의 상대 비교 왜곡(높은 점수를 '낮다'고
        # 서술하는 문제)을 원천 차단
        f"- 초년: {_graph_phase_desc(analysis['life_graph']['early'])}",
        f"- 중년: {_graph_phase_desc(analysis['life_graph']['mid'])}",
        f"- 말년: {_graph_phase_desc(analysis['life_graph']['late'])}",
        f"- 질문: {P.GRAPH_QUESTION[persona]}",
        "- 각 시기는 위에 적힌 흐름 판정과 모순되게 서술하지 마라.",
        "- summary는 1문장, 각 시기 body는 1~2문장.",
        "",
        "[마지막 한 줄]",
        f"- {P.FINAL_LINE_RULE[persona]}. 새 분석을 만들지 말고 위 해석에서 압축할 것. 25자 이내.",
    ]
    return "\n".join(lines)


def generate_persona(persona: str, analysis: dict, model: str | None = None) -> dict:
    """페르소나 1개의 해석 생성. Ollama /api/chat + format 스키마."""
    payload = {
        "model": model or MODEL,
        "messages": [{"role": "user", "content": _build_prompt(persona, analysis)}],
        "stream": False,
        "format": _section_schema(persona),
        "options": {"temperature": 0.7, "num_ctx": 4096},
    }
    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.post(f"{OLLAMA_URL}/api/chat", json=payload)
        resp.raise_for_status()
        content = resp.json()["message"]["content"]
    data = json.loads(content)

    # 객체 → 배열 변환. question_key / evidence는 상수 테이블에서 주입 (LLM에 맡기지 않음)
    sections = []
    for cat in P.CATEGORIES:
        sec = data["sections"][cat]
        sections.append({
            "category": cat,
            "question_key": f"{persona}_{cat.upper()}",
            "evidence": {
                "primary": P.PRIMARY_EVIDENCE[(persona, cat)],
                "secondary": None,
                "style": "MEDIUM",
            },
            **sec,
        })
    return {
        "analysis_id": analysis["analysis_id"],
        "persona": persona,
        "sections": sections,
        "life_graph_reading": data["life_graph_reading"],
        "final_line": data["final_line"],
    }


def check_health() -> bool:
    try:
        with httpx.Client(timeout=3.0) as client:
            return client.get(f"{OLLAMA_URL}/api/tags").status_code == 200
    except httpx.HTTPError:
        return False
