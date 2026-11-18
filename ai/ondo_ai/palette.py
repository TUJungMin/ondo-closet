"""색 이름표.

이미지 분석(대표색 이름 붙이기)과 추천(색 조합 규칙)이 같은 이름표를 쓴다.
견본(hex)은 옷에서 흔히 보이는 색조를 직접 골라 넣은 값이다. 평가에서 자주 틀리는 색이 나오면
해당 이름에 견본을 추가하는 식으로 조정한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ColorDef:
    name: str
    swatches: tuple[str, ...]
    neutral: bool = False  # 어떤 색과도 무난한 기본색
    earth: bool = False  # 베이지·갈색 계열 (서로 톤온톤)
    hue: Optional[float] = None  # 색상환 각도. 무채색은 None


PALETTE: tuple[ColorDef, ...] = (
    ColorDef("검정", ("#000000", "#151515", "#222222"), neutral=True),
    ColorDef("흰색", ("#ffffff", "#f4f4f4"), neutral=True),
    ColorDef("회색", ("#808080", "#a9a9a9", "#5a5a5a", "#c8c8c8", "#36454f"), neutral=True),
    ColorDef("아이보리", ("#f3ecd9", "#efe6d0", "#faf3e0"), neutral=True, earth=True, hue=45),
    ColorDef("베이지", ("#d9c4a1", "#c8b28e", "#e3d3b5", "#cdb99a"), neutral=True, earth=True, hue=38),
    ColorDef("카멜", ("#c19a6b", "#b5834f", "#c68e4e"), earth=True, hue=32),
    ColorDef("갈색", ("#6b4423", "#8b5a2b", "#5c4033", "#7b4b2a"), earth=True, hue=25),
    ColorDef("카키", ("#6b6b3a", "#5a5f3c", "#78704a", "#4b5320"), earth=True, hue=75),
    ColorDef("남색", ("#1f2a44", "#14213d", "#000080", "#23395d", "#2b3a55"), neutral=True, hue=225),
    ColorDef("파랑", ("#1e5aa8", "#0057b8", "#3a6ea5", "#4169e1", "#4a6a8a", "#5b7c99"), hue=215),
    ColorDef("하늘색", ("#87ceeb", "#a6c8e6", "#b5d3e7", "#9bb7d4"), hue=200),
    ColorDef("초록", ("#228b22", "#2e7d32", "#3c8d5a", "#1b5e20"), hue=130),
    ColorDef("민트", ("#98d8c8", "#a8e0d0"), hue=165),
    ColorDef("노랑", ("#f7d038", "#ffe066", "#e6b800", "#d4a72c"), hue=50),
    ColorDef("주황", ("#f28c28", "#ff7f32", "#e2711d"), hue=28),
    ColorDef("빨강", ("#d32f2f", "#c62828", "#e53935", "#b71c1c"), hue=0),
    ColorDef("버건디", ("#800020", "#6d1a2a", "#7b1e3a", "#5e1224"), hue=345),
    ColorDef("분홍", ("#f8bbd0", "#f48fb1", "#ffc0cb", "#e8739c"), hue=335),
    ColorDef("보라", ("#6a1b9a", "#7e57c2", "#8e44ad", "#b39ddb"), hue=275),
)

COLOR_BY_NAME: dict[str, ColorDef] = {c.name: c for c in PALETTE}
COLOR_NAMES: tuple[str, ...] = tuple(c.name for c in PALETTE)

# 갈색 계열과 붙였을 때 어색해지기 쉬운 색
_EARTH_AWKWARD = {"분홍", "보라", "민트"}


def hue_distance(a: float, b: float) -> float:
    d = abs(a - b) % 360
    return min(d, 360 - d)


def pair_harmony(a: Optional[str], b: Optional[str]) -> tuple[float, str]:
    """두 색 이름의 어울림 점수(0~1)와 관계 이름.

    관계: basic(기본색 포함) · same(같은 색) · tone(톤온톤) · soft(자연스러운 이어짐)
          · contrast(보색 대비) · clash(어긋남) · unknown(색 정보 없음)
    """
    ca, cb = COLOR_BY_NAME.get(a or ""), COLOR_BY_NAME.get(b or "")
    if ca is None or cb is None:
        return 0.7, "unknown"
    if ca.neutral or cb.neutral:
        if a == b:
            return 0.85, "same"
        if ca.earth and cb.earth:
            return 0.95, "tone"
        return 1.0, "basic"
    if ca.earth and cb.earth:
        return (0.8, "same") if a == b else (0.95, "tone")
    if ca.earth or cb.earth:
        other = cb if ca.earth else ca
        return (0.6, "clash") if other.name in _EARTH_AWKWARD else (0.85, "soft")
    if a == b:
        return 0.6, "same"
    d = hue_distance(ca.hue or 0.0, cb.hue or 0.0)
    if d <= 40:
        return 0.75, "soft"
    if d >= 150:
        return 0.5, "contrast"
    return 0.4, "clash"


def is_point_color(name: Optional[str]) -> bool:
    """기본색·갈색 계열이 아닌, 눈에 띄는 색인지."""
    c = COLOR_BY_NAME.get(name or "")
    return c is not None and not c.neutral and not c.earth
