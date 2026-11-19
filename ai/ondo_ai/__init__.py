"""온도옷장 AI 모듈.

- 추천 엔진: ``from ondo_ai import recommend`` (numpy, pydantic만 필요)
- 이미지 분석: ``from ondo_ai.vision import get_analyzer`` (torch 등 vision 의존성 필요)
"""

from .recommend import recommend
from .schemas import (
    AnalysisResult,
    Category,
    DetectedGarment,
    Feeling,
    Garment,
    OutfitAnalysisResult,
    Place,
    Recommendation,
    RecommendRequest,
    RecommendResult,
    Rejection,
    RejectReason,
    Sky,
    Status,
    Style,
    WearRecord,
    Weather,
)

__version__ = "0.1.0"

__all__ = [
    "recommend",
    "AnalysisResult",
    "Category",
    "DetectedGarment",
    "Feeling",
    "Garment",
    "OutfitAnalysisResult",
    "Place",
    "Recommendation",
    "RecommendRequest",
    "RecommendResult",
    "Rejection",
    "RejectReason",
    "Sky",
    "Status",
    "Style",
    "WearRecord",
    "Weather",
]
