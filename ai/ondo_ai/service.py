"""FastAPI 연결부.

AI 실행 위치가 아직 정해지지 않아(CLAUDE.md 9장) 두 가지 모두 되게 했다.

1) 백엔드 서버 안에서 직접 실행:  ``app.include_router(ondo_ai.service.router)``
2) 별도 추론 서버로 실행:        ``uvicorn ondo_ai.service:app --port 8001``

사진 분석 주소는 둘이다. 옷 한 벌 사진은 /ai/analyze, 옷이 여러 벌 찍힌 사진은 /ai/analyze-outfit.

올라온 사진은 메모리에서만 다루고 이 모듈은 디스크에 남기지 않는다. 저장은 백엔드가 맡는다.
"""

from __future__ import annotations

import base64
import io
from typing import Optional

from fastapi import APIRouter, FastAPI, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from .recommend import recommend
from .schemas import AnalysisResult, DetectedGarment, OutfitAnalysisResult, RecommendRequest, RecommendResult

_MAX_UPLOAD_BYTES = 15 * 1024 * 1024

router = APIRouter(prefix="/ai", tags=["ai"])


class AnalyzeResponse(AnalysisResult):
    cutout_png_base64: Optional[str] = None


class OutfitItemResponse(DetectedGarment):
    cutout_png_base64: Optional[str] = None


class OutfitAnalyzeResponse(OutfitAnalysisResult):
    items: list[OutfitItemResponse] = []  # type: ignore[assignment]


def _read_image(file: UploadFile) -> Image.Image:
    data = file.file.read(_MAX_UPLOAD_BYTES + 1)
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="사진이 너무 커요. 15MB 이하로 올려 주세요.")
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="사진 파일을 열 수 없어요.") from None
    return image


def _png_base64(image: Optional[Image.Image]) -> Optional[str]:
    if image is None:
        return None
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/warmup")
def warmup(outfit: bool = False) -> dict[str, str]:
    """모델을 미리 메모리에 올린다. 서버 시작 직후 한 번 불러 두면 첫 분석이 빨라진다.

    여러 옷 사진 분석(/ai/analyze-outfit)도 쓸 거라면 ``?outfit=true``로 검출 모델까지 올린다.
    """
    from .vision import get_analyzer

    analyzer = get_analyzer()
    analyzer.warmup(outfit=outfit)
    return {"status": "ready", "device": analyzer.device}


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(file: UploadFile = File(...), include_cutout: bool = True) -> AnalyzeResponse:
    """옷 한 벌이 찍힌 사진 → 종류·색상·보온성·스타일 제안과 배경 제거 이미지."""
    from .vision import get_analyzer

    result, cutout = get_analyzer().analyze_with_cutout(_read_image(file))
    response = AnalyzeResponse(**result.model_dump())
    if include_cutout:
        response.cutout_png_base64 = _png_base64(cutout)
    return response


@router.post("/analyze-outfit", response_model=OutfitAnalyzeResponse)
def analyze_outfit(file: UploadFile = File(...), include_cutout: bool = True) -> OutfitAnalyzeResponse:
    """옷이 여러 벌 찍힌 사진(착용 사진 등) → 옷별로 나눈 분석 결과와 배경 제거 이미지.

    원본 사진은 저장하지 않는다. 가방·모자·원피스처럼 옷장 종류가 아닌 것은 ``skipped``에 이름만 담는다.
    """
    from .vision import get_analyzer

    result, cutouts = get_analyzer().analyze_outfit_with_cutouts(_read_image(file))
    items = [
        OutfitItemResponse(**item.model_dump(), cutout_png_base64=_png_base64(cutout) if include_cutout else None)
        for item, cutout in zip(result.items, cutouts)
    ]
    return OutfitAnalyzeResponse(**result.model_dump(exclude={"items"}), items=items)


@router.post("/recommend", response_model=RecommendResult)
def recommend_outfits(request: RecommendRequest) -> RecommendResult:
    """고정한 옷 한 벌 + 날씨·장소·기록 → 코디 추천."""
    try:
        return recommend(request)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None


app = FastAPI(title="온도옷장 AI", version="0.1.0")
app.include_router(router)
