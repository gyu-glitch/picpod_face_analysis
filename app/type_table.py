"""20유형 상수 테이블 — 미로 v2 문서 §1-4. 생성 대상이 아니라 상수다.

유형명 20개는 미로 확정본. 태그라인은 '직진본능형'만 원문 확보 상태라
나머지 19개는 [초안]이며, 미로 별첨 네이밍 표 확보 후 교체할 것.
서브텍스트(주형 5 × 보조 4 = 20조합)도 사전 작성-조회 방식(§9 권장안) 초안.
"""

# {MAIN}_{DOMINANT} → (유형명, 태그라인)
TYPE_TABLE: dict[str, tuple[str, str]] = {
    "WOOD_UPPER":    ("플랜부자형", "머릿속에 플랜 B부터 Z까지 있다. 실행은 아직이다."),
    "WOOD_MID":      ("직진본능형", "고민할 시간에 일단 지르고 본다. 수습은 내일의 내가."),
    "WOOD_LOWER":    ("인싸군단형", "혼자 온 적이 없다. 어디서든 무리가 생긴다."),
    "WOOD_BALANCED": ("올라운더형", "뭘 시켜도 평균 이상. 본인만 그걸 모른다."),
    "FIRE_UPPER":    ("감각천재형", "설명은 못 하는데 답은 맞는다. 촉이 스펙이다."),
    "FIRE_MID":      ("완전끝장형", "시작하면 끝을 본다. 중간 저장이 없다."),
    "FIRE_LOWER":    ("시선강탈형", "가만히 있어도 주인공. 조연 체질이 아니다."),
    "FIRE_BALANCED": ("절대센터형", "센터 자리는 비워두는 게 아니라 내 자리다."),
    "EARTH_UPPER":   ("팩트체크형", "일단 검색부터 한다. 출처 없는 말은 안 믿는다."),
    "EARTH_MID":     ("마이웨이형", "남들이 뭐라든 내 속도로 간다. 어차피 도착한다."),
    "EARTH_LOWER":   ("숨은실세형", "나서지 않는데 다들 물어보러 온다."),
    "EARTH_BALANCED":("평온시크형", "흔들리는 건 남 얘기. 오늘도 평온 유지 중."),
    "METAL_UPPER":   ("냉철스캔형", "한 번 보면 파악 끝. 감정은 그다음 문제다."),
    "METAL_MID":     ("팩폭장인형", "돌려 말하면 시간 낭비. 아프면 맞는 말이다."),
    "METAL_LOWER":   ("철벽수비형", "곁을 잘 안 주지만, 한 번 들이면 평생이다."),
    "METAL_BALANCED":("칼각유지형", "흐트러짐은 계획에 없다. 각 잡힌 게 편하다."),
    "WATER_UPPER":   ("독심술사형", "말 안 해도 안다. 표정이 곧 자막이다."),
    "WATER_MID":     ("생존특화형", "어디 떨어뜨려 놔도 산다. 적응이 특기다."),
    "WATER_LOWER":   ("인간자석형", "가만히 있어도 사람이 붙는다. 끊어내는 게 숙제다."),
    "WATER_BALANCED":("만능조율형", "싸움 나면 찾는 사람. 결국 중간에서 다 맞춘다."),
}

# 태그라인 확정 여부 (미로 별첨 표 확보 후 True로)
TAGLINE_CONFIRMED = {"WOOD_MID"}

# 서브텍스트: (주형, 보조형) 20조합 사전 작성 — §9 "생성보다 조회가 안전" 권장안 채택. 전부 초안.
SUBTEXT_TABLE: dict[tuple[str, str], str] = {
    ("wood", "fire"):   "각 잡히면 일단 직진, 움직이며 답을 찾는 편",
    ("wood", "earth"):  "방향은 과감하게, 걸음은 착실하게 가는 편",
    ("wood", "metal"):  "크게 그리고 세밀하게 다듬는, 설계자 기질",
    ("wood", "water"):  "뻗어나가되 흐름을 읽는, 유연한 확장형",
    ("fire", "wood"):   "타오르는 추진력에 방향 감각까지 갖춘 편",
    ("fire", "earth"):  "화끈하게 지르고 뒷심으로 버티는 편",
    ("fire", "metal"):  "열정에 날이 서 있는, 정확한 승부사 기질",
    ("fire", "water"):  "확 타올랐다가도 금세 온도 조절하는 편",
    ("earth", "wood"):  "묵직하게 버티다 때가 오면 크게 움직이는 편",
    ("earth", "fire"):  "평소엔 잔잔, 발동 걸리면 화력 급상승",
    ("earth", "metal"): "신중하게 재고 확실할 때만 움직이는 편",
    ("earth", "water"): "무던해 보여도 속으로 다 헤아리고 있는 편",
    ("metal", "wood"):  "기준은 칼같이, 시야는 넓게 가져가는 편",
    ("metal", "fire"):  "차갑게 판단하고 뜨겁게 실행하는 편",
    ("metal", "earth"): "원칙과 꾸준함, 둘 다 놓지 않는 편",
    ("metal", "water"): "날카로운 눈에 부드러운 처세를 겸비한 편",
    ("water", "wood"):  "흐르듯 적응하다 기회에서 훅 치고 나가는 편",
    ("water", "fire"):  "느긋해 보여도 승부처에선 확 달아오르는 편",
    ("water", "earth"): "부드럽게 스며들어 오래 남는 편",
    ("water", "metal"): "유연한데 선은 확실한, 부드러운 원칙주의자",
}

_DOMINANT_CODE = {"upper": "UPPER", "mid": "MID", "lower": "LOWER", "balanced": "BALANCED"}


def resolve_type(ohaeng: dict, samjeong: dict) -> dict:
    code = f"{ohaeng['main'].upper()}_{_DOMINANT_CODE[samjeong['dominant']]}"
    name, tagline = TYPE_TABLE[code]
    subtext = SUBTEXT_TABLE[(ohaeng["main"], ohaeng["sub"])]
    return {"code": code, "name": name, "tagline": tagline, "subtext": subtext}
