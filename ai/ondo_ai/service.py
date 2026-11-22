"""FastAPI 연결부.

AI 실행 위치가 아직 정해지지 않아(CLAUDE.md 9장) 두 가지 모두 되게 했다.

1) 백엔드 서버 안에서 직접 실행:  ``app.include_router(ondo_ai.service.router)``
2) 별도 추론 서버로 실행:        ``uvicorn ondo_ai.service:app --port 8001``

사진 분석 주소는 둘이다. 옷 한 벌 사진은 /ai/analyze, 옷이 여러 벌 찍힌 사진은 /ai/analyze-outfit.

올라온 사진은 메모리에서만 다루고 이 모듈은 디스크에 남기지 않는다. 저장은 백엔드가 맡는다.

환경 변수 ``ONDO_WARMUP=outfit``으로 띄우면 서버 시작과 함께 모델을 미리 올린다(기본은 끔).
올리는 동안 /ai/health는 ``{"status": "loading"}``, 끝나면 ``{"status": "ok"}``다.
"""

from __future__ import annotations

import base64
import io
import logging
import os
import threading
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from fastapi import APIRouter, FastAPI, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from .recommend import recommend
from .schemas import AnalysisResult, DetectedGarment, OutfitAnalysisResult, RecommendRequest, RecommendResult

_MAX_UPLOAD_BYTES = 15 * 1024 * 1024

# uvicorn이 콘솔에 찍는 로거를 같이 쓴다. (따로 만든 로거는 기본 설정에서 INFO가 보이지 않는다)
_log = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/ai", tags=["ai"])

# /ai/health가 돌려주는 값. 시작 워밍업을 켰을 때만 그동안 "loading"이 된다.
_status = "ok"


def _run_warmup(outfit: bool) -> None:
    """시작 워밍업 본체. 별도 스레드에서 돈다. 실패해도 서버는 살아 있으므로 끝나면 항상 ok로 돌린다."""
    global _status
    started = time.perf_counter()
    try:
        from .vision import get_analyzer

        get_analyzer().warmup(outfit=outfit)
        _log.info("모델 워밍업 완료 (%.1f초)", time.perf_counter() - started)
    except Exception:
        # 가중치를 내려받지 못한 경우 등. 워밍업을 끈 것과 같은 상태가 되고, 첫 분석 요청 때 다시 올린다.
        _log.exception("모델 워밍업 실패. 모델은 첫 분석 요청 때 다시 올립니다.")
    finally:
        _status = "ok"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """서버 시작 때 ONDO_WARMUP=outfit이면 모델(검출 모델 포함)을 미리 올린다.

    서버가 바로 요청을 받도록 스레드에서 돌린다. 그동안 들어온 분석 요청은 모델이 올라올 때까지
    기다렸다가 처리되고, 추천(/ai/recommend)은 모델을 쓰지 않아 바로 응답한다.
    """
    global _status
    mode = os.environ.get("ONDO_WARMUP", "").strip().lower()
    if mode == "outfit":
        _status = "loading"
        threading.Thread(target=_run_warmup, kwargs={"outfit": True}, name="ondo-warmup", daemon=True).start()
    elif mode:
        _log.warning("ONDO_WARMUP=%s 은 모르는 값이라 워밍업을 하지 않습니다. (쓸 수 있는 값: outfit)", mode)
    yield


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
    """서버 상태. 시작 워밍업(ONDO_WARMUP) 중에는 ``loading``, 그 밖에는 ``ok``."""
    return {"status": _status}


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


app = FastAPI(title="온도옷장 AI", version="0.1.0", lifespan=lifespan)
app.include_router(router)
