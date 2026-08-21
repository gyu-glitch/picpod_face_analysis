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
import re
from datetime import datetime
from pathlib import Path

import httpx

from . import persona as P
from .life_graph import _seeded_random

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("GWANSANG_MODEL", "exaone3.5:2.4b")
TIMEOUT = 300.0
MAX_ATTEMPTS = 3  # 아티팩트(글자수 에코·영어 혼입) 검출 시 재생성 횟수

_SAMPLES_DIR = Path(__file__).resolve().parent.parent / "config" / "kiosk_json_update"
_style_cache: dict[str, str] = {}

# 문자 내용은 스키마로 제약하지 않는다.
# Ollama의 pattern→GBNF 변환이 JSON 문자열 이스케이프 규칙과 충돌해
# 깨진 JSON(Invalid \escape / control character)을 만든다. 실측 확인됨.
# 영어·글자수 혼입은 프롬프트 + 재생성 + _sanitize 후처리로 잡는다.
_KOTEXT = {"type": "string"}

# 디자이너 이모지 분류 체계 — 각 텍스트 블록의 톤 태그 (enum으로 문법 강제)
EMOTIONS = ["neutral", "positive", "interest", "worry", "warning", "cool", "money"]
_EMOTION = {"type": "string", "enum": EMOTIONS}


def _flat_schema(keys: list[str]) -> dict:
    """평탄한 문자열 dict 스키마.

    중첩 스키마(lifeFlow.stages.early.headline)를 쓰면 7.8B가 구조를 놓치고
    본문에 '}}, {' 같은 JSON 파편을 흘린다. 실측 확인 후 평탄 구조로 전환하고
    중첩 조립은 코드가 담당한다.
    """
    return {"type": "object",
            "properties": {k: (_EMOTION if k.endswith("_감정") else _KOTEXT) for k in keys},
            "required": keys}


# 1차 호출: 삼정·오행 해석 + 5개 카테고리
_KEYS_PART1 = ["삼정_카피", "삼정_해설", "삼정_감정", "오행_카피", "오행_해설", "오행_감정"]
for _c in P.CATEGORIES:
    _ko = P.CATEGORY_KO[_c]
    _KEYS_PART1 += [f"{_ko}_카피", f"{_ko}_해설", f"{_ko}_조언", f"{_ko}_요지", f"{_ko}_감정"]

# 2차 호출: 종합운 + 인생그래프 + 마지막 한 줄
_KEYS_PART2 = ["종합운_카피", "종합운_해설", "종합운_감정", "인생그래프_카피",
               "초년_카피", "초년_해설", "초년_감정", "중년_카피", "중년_해설", "중년_감정",
               "말년_카피", "말년_해설", "말년_감정",
               "인생그래프_조언", "마지막한줄", "마지막한줄_감정"]

_SCHEMA_PART1 = _flat_schema(_KEYS_PART1)
_SCHEMA_PART2 = _flat_schema(_KEYS_PART2)

_ELEM_KO = {"wood": "목(木)", "fire": "화(火)", "earth": "토(土)", "metal": "금(金)", "water": "수(水)"}
_DOM_KO = {"upper": "상정", "mid": "중정", "lower": "하정", "balanced": "삼정 균형"}


def _style_example(persona: str) -> str:
    """키오스크 확정 샘플(KioskData_*.json)에서 해당 페르소나의 실문장을 문체 예시로 추출."""
    kiosk = P.PERSONA_KIOSK[persona]
    if kiosk not in _style_cache:
        path = _SAMPLES_DIR / f"KioskData_{kiosk}.json"
        if not path.exists():
            _style_cache[kiosk] = ""
        else:
            r = json.loads(path.read_text(encoding="utf-8"))["reading"]
            t, f_, lf = r["temperament"], r["finances"], r["lifeFlow"]
            _style_cache[kiosk] = "\n".join([
                f"  headline 예시: 「{t['headline']}」 / 「{f_['headline']}」 / 「{lf['headline']}」",
                f"  description 예시: {t['description']}",
                f"  advice 예시: {t['advice']}",
                f"  시기 서술 예시: {lf['stages']['early']['description']}",
            ])
    return _style_cache[kiosk]


# 결과지에 섞이면 안 되는 것들
_RE_CHARCOUNT = re.compile(r"\d+\s*자")          # "(77자)", "160자 이내"
_RE_LATIN = re.compile(r"[A-Za-z]{2,}")          # 영어 단어
_RE_TAG = re.compile(r"</?[A-Za-z][^>]*>")       # <strong> 등
# 필드명 에코: 'advice: ...' 뿐 아니라 '기질_조언: ...', ', 실행력 요지: ...' 형태도 잡는다
_RE_FIELD_ECHO = re.compile(
    r"[,·\n]?\s*[\[{]?\s*[가-힣]{0,6}[_ ]?"
    r"(claim|advice|headline|description|summary|카피|해설|조언|요지)"
    r"\s*[\]\)}]?\s*[:：].*",
    re.IGNORECASE | re.DOTALL)
_RE_EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF️✀-➿]+")
# 프롬프트 지시문/필드명이 괄호째 새어 나오는 것: [각 시기에], {early], <중년>
_RE_MARKER = re.compile(r"[\[{<][^\]}>\n]{0,20}[\]}>]")
# 후보 문장을 여러 개 이어 붙일 때 쓰는 구분 기호
_RE_ALT_SEP = re.compile(r"[〇◯○]")
_RE_SCORE = re.compile(r"\d+\s*점")   # 수치 비노출 (미로 v2 §9)


def _find_artifacts(node, path: str = "") -> list[str]:
    """생성 결과의 모든 문자열 값에서 아티팩트 검출 (재생성 판단용)."""
    bad = []
    if isinstance(node, dict):
        for k, v in node.items():
            if k.endswith("_감정") or k == "emotion":
                continue  # enum 영어 값 — 아티팩트 아님
            bad += _find_artifacts(v, f"{path}.{k}" if path else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            bad += _find_artifacts(v, f"{path}[{i}]")
    elif isinstance(node, str):
        if _RE_CHARCOUNT.search(node):
            bad.append(f"{path} 글자수표기: {node[:50]}")
        if _RE_LATIN.search(node):
            bad.append(f"{path} 영어: {node[:50]}")
        if _RE_TAG.search(node) or _RE_FIELD_ECHO.search(node):
            bad.append(f"{path} 마크업/필드에코: {node[:50]}")
        if _RE_MARKER.search(node):
            bad.append(f"{path} 지시문 마커: {node[:50]}")
        if _RE_ALT_SEP.search(node):
            bad.append(f"{path} 후보 나열: {node[:50]}")
        if _RE_SCORE.search(node):
            bad.append(f"{path} 점수 노출: {node[:50]}")
        if not node.strip():
            bad.append(f"{path} 빈값")
    return bad


def _sanitize(node):
    """남은 아티팩트를 기계적으로 제거 — 재생성으로도 안 잡힌 경우의 마지막 방어선."""
    if isinstance(node, dict):
        return {k: (v if k.endswith("_감정") or k == "emotion" else _sanitize(v))
                for k, v in node.items()}
    if isinstance(node, list):
        return [_sanitize(v) for v in node]
    if isinstance(node, str):
        s = _RE_FIELD_ECHO.sub("", node)                    # 'advice: ...' 이후 통째로
        s = _RE_TAG.sub("", s)                              # HTML 태그
        s = _RE_EMOJI.sub("", s)                            # 감열지에서 깨지는 이모지
        s = _RE_MARKER.sub("", s)                           # [각 시기에], {early] 같은 마커
        s = re.sub(r"[\(\[]?\s*\d+\s*자[^.!?\n]*[\)\]]?\.?", "", s)  # 글자수 표기
        s = re.sub(r"\s*\*+\s*", " ", s)                    # 마크다운 강조 잔재
        s = re.sub(r"^\s*[-–—·]\s*", "", s)                 # 앞머리 리스트 마커
        s = _RE_ALT_SEP.split(s)[0]                          # 후보 나열이면 첫 문장만
        if len(re.findall(r"[「」]", s)) == 1:                # 짝 없는 낫표
            s = re.sub(r"[「」]", "", s)
        # 문장 끝에 덧붙은 구호 꼬리 ( ...대처하면 성공이 기다려.~ 이끌어주자 )
        s = re.sub(r"(?<=[.!?])\s*~+\s*[^.!?~]{1,20}$", "", s)
        # 문장을 이어 붙이며 남긴 따옴표 접합 흔적 ( ...해요,", "금전 흐름... )
        s = re.sub(r"[,，]{2,}", ",", s)
        s = re.sub(r"[\"“”]\s*[,，]?\s*[\"“”]", " ", s)
        if len(re.findall(r"[\"“”]", s)) == 1:               # 짝 없는 따옴표
            s = re.sub(r"[\"“”]", "", s)
        s = re.sub(r"\s+", " ", s).strip()
        s = re.sub(r"[\s,·]*[\]\)}]+$", "", s)              # 끝에 남은 닫는 괄호
        return s.strip(" ,·")
    return node


def _graph_phase_desc(score: int) -> str:
    """흐름 판정은 코드가 확정해 문구로만 전달 — 점수를 프롬프트에 넣으면
    모델이 '88점' 식으로 본문에 인용해 버린다 (미로 v2 §9 수치 비노출)."""
    if score >= 75:
        return "기세가 좋은 시기"
    if score >= 60:
        return "무난하게 흘러가는 시기"
    return "조심해야 하는 시기"


def _common_header(persona: str, analysis: dict) -> list[str]:
    oh, sj = analysis["ohaeng"], analysis["samjeong"]
    return [
        "너는 관상 풀이 작가다. 손님에게 인쇄되어 나갈 관상 풀이를 쓴다.",
        "",
        "[절대 규칙]",
        "- 완성된 문장만 써라. 지시문·항목명·괄호 표시·따옴표를 본문에 옮기지 마라.",
        "- 점수와 숫자를 쓰지 마라. 글자 수를 세지 마라.",
        "- 한국어만 써라. 영어 단어·알파벳·이모지·별표를 절대 쓰지 마라.",
        "- 모든 칸을 빠짐없이 채워라. 빈칸으로 두지 마라.",
        "- 카피는 짧고 재치 있는 비유 한 줄. 설명하지 말고 툭 던지듯 짧게.",
        "- _감정 칸은 그 블록 텍스트의 톤 태그 하나: neutral=담담한 서술 / positive=칭찬·희망"
        " / interest=흥미·호기심 / worry=걱정·조심 / warning=따끔한 경고·독설"
        " / cool=자신감·여유 / money=재물 이야기.",
        "- 해설은 2~3문장. 조언은 1~2문장. 각 칸은 자기 내용만 담고 다른 칸 내용을 섞지 마라.",
        f"- {P.COMMON_TONE}",
        "",
        f"[페르소나] {P.PERSONA_KO[persona]}",
        f"[문체] {P.PERSONA_STYLE[persona]}",
        "[문체 실예시 — 이 수위와 호흡만 따라 하고 내용은 절대 베끼지 말 것]",
        _style_example(persona),
        "",
        "[분석 대상]",
        f"- 유형: {analysis['type']['name']} — {analysis['type']['tagline']}",
        f"- 오행: 주형 {_ELEM_KO[oh['main']]} / 보조 {_ELEM_KO[oh['sub']]}",
        f"- 삼정: {P.samjeong_phrase(sj)}",
        "",
    ]


def _build_prompt_part1(persona: str, analysis: dict) -> str:
    """삼정·오행 + 5개 카테고리."""
    oh, sj = analysis["ohaeng"], analysis["samjeong"]
    lines = _common_header(persona, analysis) + [
        "[채울 칸]",
        f"- 삼정_카피 / 삼정_해설: 삼정 구조가 말하는 기질 ({_DOM_KO[sj['dominant']]} 중심).",
        f"- 오행_카피 / 오행_해설: 주형 {_ELEM_KO[oh['main']]}과 보조 {_ELEM_KO[oh['sub']]}의"
        " 조합이 드러나는 방식.",
    ]
    for cat in P.CATEGORIES:
        ko = P.CATEGORY_KO[cat]
        q = P.QUESTION_MATRIX[(persona, cat)]
        ev = P.evidence_value(P.PRIMARY_EVIDENCE[(persona, cat)], analysis)
        lines.append(
            f"- {ko}_카피 / {ko}_해설 / {ko}_조언: 「{q}」에 답하되,"
            f" 관찰된 「{ev}」를 문장 속에 자연스럽게 녹일 것."
            f" {ko}_요지는 문체를 뺀 건조한 평문 1문장(내부 검수용)."
        )
    return "\n".join(lines)


def _build_prompt_part2(persona: str, analysis: dict, part1: dict) -> str:
    """종합운 + 인생그래프 + 마지막 한 줄. part1 결과를 근거로 이어 쓴다."""
    lg = analysis["life_graph"]
    gist = " / ".join(
        part1.get(f"{P.CATEGORY_KO[c]}_요지", "") for c in P.CATEGORIES
    ).strip(" /")
    return "\n".join(_common_header(persona, analysis) + [
        "[앞서 나온 해석 요지 — 여기서 벗어나지 말 것]",
        gist or "(없음)",
        "",
        "[채울 칸]",
        "- 종합운_카피 / 종합운_해설: 위 요지 전체를 관통하는 가장 지배적인 패턴 하나.",
        "- 인생그래프_카피: 인생 흐름 전체를 한 줄로.",
        # 흐름 판정은 코드가 확정해 문구로 주입 (상대 비교 왜곡·점수 인용 방지)
        f"- 초년_카피 / 초년_해설: {_graph_phase_desc(lg['early'])}",
        f"- 중년_카피 / 중년_해설: {_graph_phase_desc(lg['mid'])}",
        f"- 말년_카피 / 말년_해설: {_graph_phase_desc(lg['late'])}",
        "- 인생그래프_조언: 세 시기를 통틀어 건네는 조언 1~2문장.",
        f"- 마지막한줄: {P.FINAL_LINE_RULE[persona]}."
        " 새 분석을 만들지 말고 위 해석에서 압축한 짧은 한 문장.",
        "",
        f"[시기를 보는 관점] {P.GRAPH_QUESTION[persona]}",
        "- 위 시기 판정과 모순되게 쓰지 마라. 관점 문구나 시기 이름을 본문에 옮기지 마라.",
    ])


def _generate_block(prompt: str, schema: dict, keys: list[str],
                    model: str | None, label: str) -> dict:
    """한 블록을 생성하고, 아티팩트가 있으면 온도를 낮춰 재생성. 가장 깨끗한 결과 채택."""
    best, best_artifacts = None, None
    for attempt in range(MAX_ATTEMPTS):
        payload = {
            "model": model or MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": schema,
            "options": {
                "temperature": 0.7 - attempt * 0.2,   # 재시도마다 보수적으로
                "num_ctx": 4096,
                "num_predict": 2500,
                "repeat_penalty": 1.1,
            },
        }
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.post(f"{OLLAMA_URL}/api/chat", json=payload)
            resp.raise_for_status()
            content = resp.json()["message"]["content"]
        try:
            candidate = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"[llm] {label} 시도 {attempt + 1}: JSON 파싱 실패 ({e})")
            continue

        candidate = _sanitize(candidate)          # 먼저 정제한 뒤 판정
        missing = [k for k in keys if not candidate.get(k, "").strip()]
        artifacts = _find_artifacts(candidate) + [f"{k} 빈값" for k in missing]
        if not artifacts:
            return candidate
        if best_artifacts is None or len(artifacts) < len(best_artifacts):
            best, best_artifacts = candidate, artifacts
        print(f"[llm] {label} 시도 {attempt + 1}: 아티팩트 {len(artifacts)}건 {artifacts[:2]}")

    if best is None:
        raise RuntimeError("모델이 유효한 JSON을 만들지 못했습니다. Ollama 상태를 확인하세요.")
    return best


def generate_reading(persona: str, analysis: dict, model: str | None = None) -> dict:
    """페르소나 1개의 해석 생성 → (평탄 결과 dict, 검수용 요지).

    2회로 나눠 호출한다 — 한 번에 전부 만들게 하면 7.8B가 구조를 놓치고
    본문에 JSON 파편·지시문을 흘린다 (실측 확인).
    """
    part1 = _generate_block(_build_prompt_part1(persona, analysis),
                            _SCHEMA_PART1, _KEYS_PART1, model, f"{persona}/1")
    part2 = _generate_block(_build_prompt_part2(persona, analysis, part1),
                            _SCHEMA_PART2, _KEYS_PART2, model, f"{persona}/2")
    out = {**part1, **part2}
    claims = {cat: out.pop(f"{P.CATEGORY_KO[cat]}_요지", "") for cat in P.CATEGORIES}
    return out, claims


def _print_code(analysis_id: str, persona: str) -> str:
    return f"{int(_seeded_random(analysis_id, f'print:{persona}') * 100000):05d}"


def assemble_kiosk_data(persona: str, analysis: dict, out: dict,
                        session_id: str | None = None) -> dict:
    """평탄한 LLM 출력 + 공통 분석 → 키오스크 소비 JSON (KioskData_*.json 스키마).

    중첩 구조 조립은 전부 여기서 한다 (모델은 평탄한 칸만 채운다).
    """
    sj, oh = analysis["samjeong"], analysis["ohaeng"]
    now = datetime.now().astimezone()
    dominant_map = {"upper": "upper", "mid": "middle", "lower": "lower", "balanced": "balanced"}

    def emo(prefix: str) -> str:
        v = out.get(f"{prefix}_감정", "")
        return v if v in EMOTIONS else "neutral"

    def hd(prefix: str) -> dict:
        return {"headline": out.get(f"{prefix}_카피", ""),
                "description": out.get(f"{prefix}_해설", ""),
                "emotion": emo(prefix)}

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
                    **hd("삼정"),
                },
                "fiveElements": {
                    "scores": {e: oh[e] for e in ("wood", "fire", "earth", "metal", "water")},
                    "primary": oh["main"],
                    "secondary": oh["sub"],
                    **hd("오행"),
                },
            },
            **{cat: {"headline": out.get(f"{P.CATEGORY_KO[cat]}_카피", ""),
                     "description": out.get(f"{P.CATEGORY_KO[cat]}_해설", ""),
                     "advice": out.get(f"{P.CATEGORY_KO[cat]}_조언", ""),
                     "emotion": emo(P.CATEGORY_KO[cat])}
               for cat in P.CATEGORIES},
            "overallFortune": hd("종합운"),
            "lifeFlow": {
                "headline": out.get("인생그래프_카피", ""),
                "stages": {"early": hd("초년"), "middle": hd("중년"), "later": hd("말년")},
                "advice": out.get("인생그래프_조언", ""),
            },
            "closingMessage": {"description": out.get("마지막한줄", ""),
                               "emotion": emo("마지막한줄")},
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
