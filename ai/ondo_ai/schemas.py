"""백엔드·프론트와 주고받는 데이터 형식.

값은 화면에 그대로 쓰는 한글 문자열이다. (CLAUDE.md 6장 '옷 데이터 항목' 기준)
장소(Place)와 스타일(Style) 목록은 명세에 없어 여기서 기본안을 정했다. 팀 확정 시 이 파일만 고치면 된다.
"""

from __future__ import annotations

import datetime as dt
from enum import Enum
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field

GarmentId = Union[int, str]


class Category(str, Enum):
    TOP = "상의"
    PANTS = "바지"
    SKIRT = "스커트"
    OUTER = "겉옷"
    SHOES = "신발"


# 종류 → 코디에서의 자리. 바지와 스커트는 같은 자리(하의)에 들어간다.
SLOT_OF: dict[Category, str] = {
    Category.TOP: "상의",
    Category.PANTS: "하의",
    Category.SKIRT: "하의",
    Category.OUTER: "겉옷",
    Category.SHOES: "신발",
}
UNSORTED = "미분류"


def slot_name(category: Union[Category, str, None]) -> str:
    """종류(또는 그 한글 값)가 들어가는 자리 이름: 상의 · 하의 · 겉옷 · 신발. 종류를 모르면 '미분류'."""
    try:
        return SLOT_OF[Category(category)]
    except ValueError:
        return UNSORTED


class Status(str, Enum):
    AVAILABLE = "입을 수 있음"
    LAUNDRY = "세탁"
    DRYING = "건조"
    REPAIR = "수선"


class Style(str, Enum):
    CASUAL = "캐주얼"
    FORMAL = "포멀"
    SPORTY = "스포티"
    STREET = "스트릿"
    FEMININE = "페미닌"


class Place(str, Enum):
    DAILY = "일상"
    OFFICE = "출근"
    FORMAL = "격식"
    DATE = "데이트"
    OUTDOOR = "야외활동"
    SPORT = "운동"


class Sky(str, Enum):
    CLEAR = "맑음"
    CLOUDY = "흐림"
    RAIN = "비"
    SNOW = "눈"


class Feeling(str, Enum):
    COLD = "추웠어요"
    OK = "적당했어요"
    HOT = "더웠어요"


class RejectReason(str, Enum):
    TOO_THIN = "너무 얇음"
    COLOR = "색이 안 맞음"
    PLACE = "장소에 안 맞음"
    OTHER = "직접 입력"


# ---------------------------------------------------------------- 옷


class Photo(BaseModel):
    original: Optional[str] = None
    cutout: Optional[str] = None


class Garment(BaseModel):
    id: GarmentId
    name: str = ""
    category: Category
    colors: list[str] = Field(default_factory=list, max_length=2, description="대표색 이름, 최대 2개")
    warmth: Optional[int] = Field(None, ge=1, le=5, description="보온성 1(한여름용)~5(한겨울용)")
    style: Optional[Style] = None
    status: Status = Status.AVAILABLE
    favorite: bool = False
    waterproof: bool = False
    grip: bool = False
    photo: Optional[Photo] = None

    @property
    def display_name(self) -> str:
        if self.name.strip():
            return self.name.strip()
        color = f"{self.colors[0]} " if self.colors else ""
        return f"{color}{self.category.value}"


# ---------------------------------------------------------------- 추천 입력


class Weather(BaseModel):
    temp_c: float = Field(description="외출 시간대 대표 기온")
    feels_like_c: Optional[float] = Field(None, description="체감 온도. 없으면 바람으로 추정한다")
    temp_min_c: Optional[float] = None
    temp_max_c: Optional[float] = None
    sky: Sky = Sky.CLEAR
    precip_prob: Optional[float] = Field(None, ge=0, le=1, description="강수 확률 0~1")
    wind_ms: Optional[float] = Field(None, ge=0)


class WearRecord(BaseModel):
    """착용 후 기록. feeling은 추웠어요·적당했어요·더웠어요."""

    date: dt.date
    item_ids: list[GarmentId]
    temp_c: float = Field(description="입은 날의 체감 기준 기온")
    feeling: Optional[Feeling] = None
    satisfaction: Optional[int] = Field(None, ge=1, le=5)
    place: Optional[Place] = None


class Rejection(BaseModel):
    """추천 거절 기록."""

    date: Optional[dt.date] = None
    item_ids: list[GarmentId]
    pinned_id: Optional[GarmentId] = None
    reason: RejectReason
    note: str = ""
    temp_c: Optional[float] = None
    place: Optional[Place] = None


class RecommendRequest(BaseModel):
    wardrobe: list[Garment]
    pinned_id: GarmentId
    weather: Weather
    place: Place = Place.DAILY
    wear_history: list[WearRecord] = Field(default_factory=list)
    rejections: list[Rejection] = Field(default_factory=list)
    top_k: int = Field(3, ge=1, le=10)
    today: Optional[dt.date] = None


# ---------------------------------------------------------------- 추천 출력

BasisKind = Literal["날씨", "고정 옷", "체감 기록", "거절 이유", "장소", "옷 상태"]


class Basis(BaseModel):
    kind: BasisKind
    text: str


class OutfitItem(BaseModel):
    slot: Literal["상의", "하의", "겉옷", "신발"]
    garment_id: GarmentId
    name: str
    category: Category
    pinned: bool = False


class Recommendation(BaseModel):
    rank: int
    items: list[OutfitItem]
    score: float = Field(description="0~100")
    reason: str = Field(description="왜 이 조합인지 한 줄")
    basis: list[Basis]
    breakdown: dict[str, float] = Field(description="항목별 점수 0~1 (보온·색·스타일·날씨 대비·선호)")


class ExcludedGarment(BaseModel):
    garment_id: GarmentId
    name: str
    status: Status
    text: str


class RecommendContext(BaseModel):
    apparent_temp_c: float = Field(description="날씨 기준 체감 온도")
    personal_offset_c: float = Field(description="체감 기록으로 구한 개인 보정. 음수면 추위를 타는 편")
    effective_temp_c: float = Field(description="추천에 실제로 쓴 온도 = 체감 + 개인 보정")
    wet: bool
    snowy: bool
    diurnal_range_c: Optional[float] = None
    feedback_counts: dict[str, int] = Field(default_factory=dict)


class RecommendResult(BaseModel):
    recommendations: list[Recommendation]
    excluded: list[ExcludedGarment] = Field(description="세탁·건조·수선 중이라 뺀 옷")
    context: RecommendContext
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------- 이미지 분석 출력


class Candidate(BaseModel):
    label: str
    score: float


class Suggestion(BaseModel):
    """AI 제안 한 항목. 확신이 낮으면 value는 None이고 candidates만 채운다."""

    value: Union[str, int, None] = None
    confidence: float = 0.0
    candidates: list[Candidate] = Field(default_factory=list)


class ColorInfo(BaseModel):
    name: str
    hex: str
    ratio: float = Field(description="옷 픽셀 중 차지하는 비율 0~1")


class AnalysisResult(BaseModel):
    source: Literal["ai"] = "ai"
    category: Suggestion = Field(default_factory=Suggestion)
    subtype: Suggestion = Field(default_factory=Suggestion, description="세부 종류 (니트, 청바지 등)")
    name_suggestion: Optional[str] = None
    colors: list[ColorInfo] = Field(default_factory=list)
    warmth: Suggestion = Field(default_factory=Suggestion)
    style: Suggestion = Field(default_factory=Suggestion)
    waterproof: Optional[bool] = None
    grip: Optional[bool] = None
    cutout_path: Optional[str] = None
    foreground_ratio: Optional[float] = None
    warnings: list[str] = Field(default_factory=list)
    timings_ms: dict[str, float] = Field(default_factory=dict)
    models: dict[str, str] = Field(default_factory=dict)


class DetectedGarment(BaseModel):
    """여러 옷 사진에서 찾아낸 옷 한 벌."""

    box: list[float] = Field(description="사진 안 위치 [왼쪽, 위, 오른쪽, 아래]. 가로·세로 대비 0~1")
    detector_label: str = Field(description="검출 모델이 붙인 이름 (예: jacket, pants, shoe)")
    detector_score: float
    analysis: AnalysisResult


class OutfitAnalysisResult(BaseModel):
    """한 장에 옷이 여러 벌인 사진(착용 사진 등)의 분석 결과. 옷마다 AnalysisResult 하나."""

    source: Literal["ai"] = "ai"
    items: list[DetectedGarment] = Field(default_factory=list, description="위에서 아래 순서")
    skipped: list[str] = Field(default_factory=list, description="찾았지만 옷장 종류가 아니라 뺀 것 (가방, 원피스 등)")
    warnings: list[str] = Field(default_factory=list)
    timings_ms: dict[str, float] = Field(default_factory=dict)
    models: dict[str, str] = Field(default_factory=dict)
