"""인생그래프 생성 — 미로 '인생 그래프 생성 구조' 프레임의 JS 스펙을 파이썬 포팅.

- 삼정 점수(초/중/말년)가 골격, sessionId 시드 노이즈로 8포인트 곡선 생성.
- 같은 sessionId → 항상 같은 그래프 (결정론).
- 오프셋(-18)은 표시용일 뿐 DB 원본 점수는 보존.
- 동일 SVG 로직을 영수증·포토카드 출력에 재사용할 수 있게 마크업 문자열 반환.
"""

LIFE_GRAPH_SCORE_OFFSET = 18
LAYOUT = {"width": 460, "height": 320, "pad_left": 24, "pad_right": 34, "pad_top": 44, "pad_bottom": 46}


def _seeded_random(session_id: str, key: str) -> float:
    """FNV-1a 해시 기반 결정론적 의사난수 [0, 1)."""
    h = 0x811C9DC5
    for ch in f"{session_id}:{key}":
        h ^= ord(ch)
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h / 0x100000000


def _fixed_random(session_id: str, key: str, lo: float, hi: float) -> float:
    return lo + _seeded_random(session_id, key) * (hi - lo)


def _clamp(v: float) -> float:
    return max(0.0, min(100.0, v))


def build_chart_points(session_id: str, scores: dict) -> list[float]:
    """8개 차트 포인트: 삼정 3점 + 구간 전환 보간점 + 시드 노이즈."""
    u = scores["early"] - LIFE_GRAPH_SCORE_OFFSET
    m = scores["mid"] - LIFE_GRAPH_SCORE_OFFSET
    l = scores["late"] - LIFE_GRAPH_SCORE_OFFSET

    def n(key, lo=-6.0, hi=6.0):
        return _fixed_random(session_id, key, lo, hi)

    points = [
        u + n("p0"),
        u + n("p1", -8, 4),
        u + (m - u) * 0.4 + n("p2", -4, 4),   # 상→중 전환
        m + (u - m) * 0.25 + n("p3", -4, 4),
        m + n("p4", -3, 3),
        m + n("p5", -2, 2),                    # 중년 정점 부근
        m + (l - m) * 0.55 + n("p6", -4, 4),   # 중→말 전환
        l + n("p7", -3, 3),
    ]
    return [_clamp(p) for p in points]


def build_svg(session_id: str, scores: dict) -> str:
    """평운 기준선 + 면 채움 + 라인 + 8포인트 마커의 완성 SVG 마크업."""
    pts = build_chart_points(session_id, scores)
    L = LAYOUT
    plot_w = L["width"] - L["pad_left"] - L["pad_right"]
    plot_h = L["height"] - L["pad_top"] - L["pad_bottom"]

    def px(i):
        return L["pad_left"] + plot_w * i / (len(pts) - 1)

    def py(score):
        return L["pad_top"] + plot_h * (1 - score / 100)

    coords = [(px(i), py(p)) for i, p in enumerate(pts)]
    line_path = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in coords)
    area_path = (
        line_path
        + f" L {coords[-1][0]:.1f} {L['height'] - L['pad_bottom']}"
        + f" L {coords[0][0]:.1f} {L['height'] - L['pad_bottom']} Z"
    )
    baseline_y = py(50)
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="#fff"/>' for x, y in coords)
    labels = "".join(
        f'<text x="{L["pad_left"] + plot_w * fx:.0f}" y="{L["height"] - 16}" fill="#fff" '
        f'font-size="13" text-anchor="middle" opacity=".85">{t}</text>'
        for fx, t in [(0.12, "초년"), (0.5, "중년"), (0.88, "말년")]
    )
    return (
        f'<svg viewBox="0 0 {L["width"]} {L["height"]}" xmlns="http://www.w3.org/2000/svg">'
        f'<line x1="{L["pad_left"]}" y1="{baseline_y:.1f}" x2="{L["width"] - L["pad_right"]}" '
        f'y2="{baseline_y:.1f}" stroke="#fff" stroke-dasharray="5 5" opacity=".4"/>'
        f'<path d="{area_path}" fill="#fff" opacity=".25"/>'
        f'<path d="{line_path}" fill="none" stroke="#fff" stroke-width="2.5"/>'
        f"{dots}{labels}</svg>"
    )
