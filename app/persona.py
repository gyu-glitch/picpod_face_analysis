"""페르소나 분기 상수 — 미로 v2 문서 §3~§6.

- 질문 매트릭스 (5 카테고리 × 3 페르소나 = 15): 고정 상수, 런타임 생성 금지.
- PRIMARY 근거 할당표: 15셀 × 15근거 1:1 — 중복이 구조적으로 불가능.
- 문체 규칙: 마지막 단계에서 한 번만 적용.
"""

# 카테고리 키는 키오스크 소비 포맷(KioskData_*.json)과 동일하게 맞춘다
CATEGORIES = ["temperament", "relationships", "finances", "executionAbility", "health"]
CATEGORY_KO = {
    "temperament": "기질", "relationships": "대인관계", "finances": "금전",
    "executionAbility": "실행력", "health": "건강·생활",
}
PERSONAS = ["KIND", "T", "ROAST"]
PERSONA_KO = {"KIND": "다정다감", "T": "완전T", "ROAST": "독설가"}
# 키오스크 personaType 표기
PERSONA_KIOSK = {"KIND": "kind", "T": "factos", "ROAST": "spicy"}
PERSONA_FROM_KIOSK = {v: k for k, v in PERSONA_KIOSK.items()}

# §3 카테고리별 질문 매트릭스
QUESTION_MATRIX: dict[tuple[str, str], str] = {
    ("KIND", "temperament"):        "나를 살리는 힘은 무엇인가",
    ("T", "temperament"):           "판단 구조는 어떻게 작동하는가",
    ("ROAST", "temperament"):       "자기 발목을 잡는 성향은 무엇인가",
    ("KIND", "relationships"):      "복이 되는 관계는 어떤 관계인가",
    ("T", "relationships"):         "관계를 어떤 방식으로 운영하는가",
    ("ROAST", "relationships"):     "관계에서 반복해서 보는 손해는 무엇인가",
    ("KIND", "finances"):           "돈과 기회가 붙는 경로는 어디인가",
    ("T", "finances"):              "돈의 의사결정과 축적 구조는 어떠한가",
    ("ROAST", "finances"):          "돈이 새는 반복 패턴은 무엇인가",
    ("KIND", "executionAbility"):   "어떤 환경에서 잘 풀리는가",
    ("T", "executionAbility"):      "실행 프로세스는 어떻게 구성되는가",
    ("ROAST", "executionAbility"):  "일을 꼬이게 하는 습관은 무엇인가",
    ("KIND", "health"):             "무엇이 나를 회복시키는가",
    ("T", "health"):                "에너지를 어떻게 운영하는가",
    ("ROAST", "health"):            "컨디션을 망치는 습관은 무엇인가",
}

# §4 근거 풀 15개: 키 → (한국어명, 분석 데이터에서 값을 뽑는 방법)
EVIDENCE_POOL = {
    "FOREHEAD_UPPER": "이마·상정",
    "EYEBROW": "눈썹",
    "GLABELLA": "미간",
    "EYE": "눈",
    "CHEEKBONE": "광대",
    "NOSE": "코",
    "PHILTRUM": "인중",
    "MOUTH": "입",
    "JAW_CHIN": "턱·하관",
    "FACE_SHAPE": "얼굴윤곽",
    "SYMMETRY": "좌우균형",
    "SAMJEONG_RATIO": "삼정비율",
    "OHAENG_MAIN": "오행 주형",
    "OHAENG_SUB": "오행 보조형",
    "MID_ZONE": "중정",
}

# §4 PRIMARY 할당표 — (페르소나, 카테고리) → 근거 키. 15셀 = 15근거 전부 사용.
PRIMARY_EVIDENCE: dict[tuple[str, str], str] = {
    ("KIND", "temperament"):        "OHAENG_MAIN",
    ("T", "temperament"):           "EYEBROW",
    ("ROAST", "temperament"):       "JAW_CHIN",
    ("KIND", "relationships"):      "EYE",
    ("T", "relationships"):         "MOUTH",
    ("ROAST", "relationships"):     "CHEEKBONE",
    ("KIND", "finances"):           "NOSE",
    ("T", "finances"):              "SAMJEONG_RATIO",
    ("ROAST", "finances"):          "PHILTRUM",
    ("KIND", "executionAbility"):   "FOREHEAD_UPPER",
    ("T", "executionAbility"):      "MID_ZONE",
    ("ROAST", "executionAbility"):  "GLABELLA",
    ("KIND", "health"):             "FACE_SHAPE",
    ("T", "health"):                "SYMMETRY",
    ("ROAST", "health"):            "OHAENG_SUB",
}

# §6 문체 규칙 (프롬프트 주입용)
PERSONA_STYLE = {
    "KIND": (
        "문장 구조: 따뜻함 → 해맑은 팩트 → 긍정적 회수. "
        "다정하고 응원하는 반말. 챙기는 어미(~해줘, ~하자)는 섹션당 1회 이하."
    ),
    "T": (
        "문장 구조: 정확한 구분 → 정정 → 효율적 조언. "
        "감정 배제, 구조와 조건 중심의 건조한 반말. 수식어 최소화."
    ),
    "ROAST": (
        "문장 구조: 먼저 때림 → 근거 → 한 번 더 때림. "
        "뼈 때리는 직설 반말. 비하가 아닌 팩트 기반 독설, 말장난 허용."
    ),
}

COMMON_TONE = "공통 톤: 반말 / 짧은 단정문 / 말장난 허용. 존댓말 금지."

# §7 인생그래프 질문
GRAPH_QUESTION = {
    "KIND": "각 시기에 무엇이 내 편이 되는가",
    "T": "각 시기에 어떤 전략이 가장 효율적인가",
    "ROAST": "각 시기에 어떤 행동이 흐름을 망치는가",
}

# §8 마지막 한 줄
FINAL_LINE_RULE = {
    "KIND": "전체 해석에서 가장 지배적인 패턴 중 '오래 가져가면 좋은 것' 하나를 압축",
    "T": "전체 해석에서 가장 지배적인 패턴 중 '기억할 운영 원칙' 하나를 압축",
    "ROAST": "전체 해석에서 가장 지배적인 패턴 중 '끊어야 할 습관' 하나를 압축",
}


ELEM_KO = {"wood": "목(木)", "fire": "화(火)", "earth": "토(土)", "metal": "금(金)", "water": "수(水)"}
_ZONE_KO = {"upper": "상정(이마)", "mid": "중정(눈~코)", "lower": "하정(입~턱)"}


def samjeong_phrase(samjeong: dict) -> str:
    """삼정 점수를 숫자 없이 서열 문장으로 — 결과지에 수치를 노출하지 않기 위함
    (미로 v2 문서 §9: 오행·삼정 수치는 화면에 노출하지 않는다)."""
    if samjeong["dominant"] == "balanced":
        return "세 구간이 고르게 균형 잡힘"
    ranked = sorted(("upper", "mid", "lower"), key=lambda z: samjeong[z], reverse=True)
    return f"{_ZONE_KO[ranked[0]]}이 가장 발달, {_ZONE_KO[ranked[-1]]}은 상대적으로 약함"


def evidence_value(key: str, analysis: dict) -> str:
    """근거 키에 해당하는 관찰 라벨을 프롬프트용 문자열로 변환 (수치 제외)."""
    b = analysis["buckets"]
    oh, sj = analysis["ohaeng"], analysis["samjeong"]
    mapping = {
        "FOREHEAD_UPPER": f"이마: {b.get('이마 너비', '')}",
        "EYEBROW": f"눈썹: {b.get('눈썹 아치', '')}",
        "GLABELLA": "미간: 두 눈썹 사이 간격",
        "EYE": f"눈: {b.get('눈 크기(세로 비율)', '')}, {b.get('눈꼬리 각도', '')}, {b.get('눈 사이 간격', '')}",
        "CHEEKBONE": f"광대·얼굴 폭: {b.get('얼굴 비율', '')}",
        "NOSE": f"코: {b.get('콧대 길이', '')}, {b.get('콧방울 너비', '')}",
        "PHILTRUM": f"인중: {b.get('인중 길이', '')}",
        "MOUTH": f"입: {b.get('입 크기', '')}, {b.get('입술 두께', '')}, {b.get('입꼬리', '')}",
        "JAW_CHIN": f"턱·하관: {b.get('턱 폭', '')}, {b.get('턱선 각도', '')}",
        "FACE_SHAPE": f"얼굴윤곽: {b.get('얼굴 비율', '')}",
        "SYMMETRY": f"좌우균형: {b.get('좌우 균형', '')}",
        "SAMJEONG_RATIO": f"삼정: {samjeong_phrase(sj)}",
        "OHAENG_MAIN": f"오행 주형: {ELEM_KO[oh['main']]}형",
        "OHAENG_SUB": f"오행 보조형: {ELEM_KO[oh['sub']]}형",
        "MID_ZONE": f"중정: {b.get('삼정 비율', '')}",
    }
    return mapping[key]
