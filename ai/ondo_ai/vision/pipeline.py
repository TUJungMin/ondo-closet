"""옷 사진 분석.

- analyze: 옷 한 벌이 찍힌 사진. 배경 제거 → 대표색 → 종류·보온성·스타일 제안.
- analyze_outfit: 한 장에 옷이 여러 벌인 사진(착용 사진 등). 옷 위치를 먼저 찾고 옷마다 위 과정을 돌린다.

모든 단계는 서버 안에서 실행한다. 사진을 외부로 보내지 않고, 이 모듈은 원본 사진을 저장하지 않는다.
한 단계가 실패해도 나머지는 계속하고, 실패한 항목은 비워 둔 채 warnings에 이유를 남긴다.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Collection
from pathlib import Path
from typing import Optional, Union

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageOps

from .. import config
from ..schemas import AnalysisResult, Category, DetectedGarment, OutfitAnalysisResult, slot_name
from . import background
from .attributes import suggest_attributes
from .classifier import ZeroShotClassifier, build_classifier
from .color import extract_colors
from .detect import GarmentDetector, GarmentRegion, contained, select_garments

ImageInput = Union[str, Path, Image.Image]

_BOX_PADDING = 0.02  # 검출 상자를 이만큼 넓혀서 자른다
_REGION_MIN_FILL = 0.15  # 상자 안에서 옷 영역이 이보다 적으면 색을 믿지 않는다
_OVERLAP_FOR_COLOR = 0.30  # 상자의 이만큼이 다른 부위 옷과 겹치면 그 옷의 색이 섞였다고 본다


def load_image(source: ImageInput) -> Image.Image:
    """사진을 열고, 휴대폰 사진의 회전 정보를 반영하고, 너무 크면 줄인다.

    투명 배경 PNG는 흰 바탕에 올린다. 그냥 RGB로 바꾸면 투명한 곳이 검정으로 읽혀 색과 분류가 틀어진다.
    """
    image = source if isinstance(source, Image.Image) else Image.open(source)
    image = ImageOps.exif_transpose(image)
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        canvas = Image.new("RGB", rgba.size, (255, 255, 255))
        canvas.paste(rgba, mask=rgba.getchannel("A"))
        image = canvas
    else:
        image = image.convert("RGB")
    if max(image.size) > config.MAX_IMAGE_SIDE:
        image.thumbnail((config.MAX_IMAGE_SIDE, config.MAX_IMAGE_SIDE), Image.LANCZOS)
    return image


def save_by_category(
    cutout: Optional[Image.Image], analysis: AnalysisResult, cutout_dir: Union[str, Path], name: str
) -> Optional[Path]:
    """배경 제거 이미지를 종류별 폴더에 저장한다: `<cutout_dir>/<상의|하의|겉옷|신발>/<name>.png`.

    바지와 스커트는 '하의' 폴더에 함께 들어간다. AI가 종류를 정하지 못한 옷은 '미분류' 폴더로 간다.
    저장한 경로를 analysis.cutout_path에 적고 돌려준다. 배경 제거 이미지가 없으면 아무것도 하지 않는다.
    """
    if cutout is None:
        return None
    folder = Path(cutout_dir) / slot_name(analysis.category.value)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.png"
    cutout.save(path)
    analysis.cutout_path = str(path)
    return path


def _stem(source: ImageInput, default: str) -> str:
    return Path(source).stem if isinstance(source, (str, Path)) else default


def layer_duplicates(items: list[DetectedGarment], regions: list[str]) -> set[int]:
    """같은 옷이 두 번 잡힌 것으로 보이는 항목의 번호를 돌려준다.

    검출 모델은 후드티 한 벌을 'jacket' 큰 상자와 그 안의 'top' 작은 상자로 두 번 잡곤 한다.
    같은 부위에서 한 상자가 다른 상자 안에 들어 있고, 분석한 종류나 대표색이 같으면 같은 옷으로 보고
    안쪽 것을 뺀다. 종류도 색도 다르면 겹쳐 입은 옷으로 보고 둘 다 둔다.
    (같은 색 옷을 겹쳐 입은 경우 안쪽 옷을 놓치는 대신, 한 벌을 두 벌로 세지 않는 쪽을 택했다.)
    부위가 다르면 상자가 겹쳐도 다른 옷이다. (바지 상자 아래쪽에 걸친 신발 등)
    """

    def primary(item: DetectedGarment) -> Optional[str]:
        return item.analysis.colors[0].name if item.analysis.colors else None

    def box(item: DetectedGarment) -> tuple[float, float, float, float]:
        return (item.box[0], item.box[1], item.box[2], item.box[3])

    dropped: set[int] = set()
    for i, inner in enumerate(items):
        for j, outer in enumerate(items):
            if i == j or regions[i] != regions[j]:
                continue
            if contained(box(inner), box(outer)) < config.DETECT_CONTAINED:
                continue
            if contained(box(outer), box(inner)) >= config.DETECT_CONTAINED:
                continue  # 서로가 서로를 덮는 경우는 앞 단계(겹침 기준)에서 이미 정리됐다
            same_category = inner.analysis.category.value == outer.analysis.category.value
            same_color = primary(inner) is not None and primary(inner) == primary(outer)
            if same_category or same_color:
                dropped.add(i)
                break
    return dropped


def strip_overlapping_colors(items: list[DetectedGarment], regions: list[str]) -> None:
    """다른 부위의 옷과 크게 겹치는 옷에서, 그 옷의 대표색을 색 목록에서 뺀다.

    착용 사진에서는 바짓단이 신발 위를 덮어, 신발 상자 안의 절반이 바지 색이 된다.
    상자의 30% 이상이 다른 부위 옷의 상자와 겹치고, 색이 둘 이상 뽑혔을 때만 적용한다.
    (검정 바지에 검정·흰색 신발이면 신발의 검정도 빠진다. 사용자가 고칠 수 있는 쪽의 오류다.)
    """
    for i, item in enumerate(items):
        box = (item.box[0], item.box[1], item.box[2], item.box[3])
        for j, other in enumerate(items):
            if i == j or regions[i] == regions[j] or not other.analysis.colors:
                continue
            other_box = (other.box[0], other.box[1], other.box[2], other.box[3])
            if contained(box, other_box) < _OVERLAP_FOR_COLOR:
                continue
            remaining = [c for c in item.analysis.colors if c.name != other.analysis.colors[0].name]
            if remaining and len(remaining) < len(item.analysis.colors):
                item.analysis.colors = remaining


class GarmentAnalyzer:
    def __init__(
        self,
        device: Optional[str] = None,
        classifier: Optional[ZeroShotClassifier] = None,
        remove_background: bool = True,
        classify_on: Optional[str] = None,
    ):
        self.device = config.resolve_device(device)
        self.classify_on = classify_on or config.CLASSIFY_ON
        self._lock = threading.Lock()  # 모델은 한 번에 한 요청만 쓴다
        self._classifier = classifier
        self._remover: Optional[background.BiRefNetRemover] = None
        self._detector: Optional[GarmentDetector] = None
        self._remove_background = remove_background

    @property
    def classifier(self) -> ZeroShotClassifier:
        if self._classifier is None:
            self._classifier = build_classifier(self.device)
        return self._classifier

    @property
    def remover(self) -> Optional[background.BiRefNetRemover]:
        if self._remove_background and self._remover is None:
            self._remover = background.BiRefNetRemover(self.device)
        return self._remover

    @property
    def detector(self) -> GarmentDetector:
        if self._detector is None:
            self._detector = GarmentDetector(self.device)
        return self._detector

    def warmup(self, outfit: bool = False) -> None:
        """서버 시작 때 불러 둔다. 모델을 올리고 빈 사진으로 한 번 돌려 첫 요청 지연을 없앤다.

        (GPU에서는 첫 추론에만 십수 초가 걸린다.) outfit=True면 여러 옷 사진용 검출 모델도 올린다.
        """
        blank = Image.new("RGB", (256, 256), (128, 128, 128))
        with self._lock:
            _ = self.classifier
            _ = self.remover
            if outfit:
                self.detector.detect(blank)
        self.analyze_with_cutout(blank)

    # ------------------------------------------------------------ 옷 한 벌 사진

    def analyze(
        self,
        source: ImageInput,
        cutout_path: Union[str, Path, None] = None,
        cutout_dir: Union[str, Path, None] = None,
    ) -> AnalysisResult:
        """사진을 분석한다. 배경 제거 이미지(PNG)를 저장하는 방법은 둘 중 하나다.

        - cutout_path: 그 경로에 그대로 저장한다.
        - cutout_dir: 종류별 폴더에 저장한다. `<cutout_dir>/<상의|하의|겉옷|신발|미분류>/<사진이름>.png`
        """
        result, cutout = self.analyze_with_cutout(source)
        if cutout is not None and cutout_path is not None:
            Path(cutout_path).parent.mkdir(parents=True, exist_ok=True)
            cutout.save(cutout_path)
            result.cutout_path = str(cutout_path)
        elif cutout_dir is not None:
            save_by_category(cutout, result, cutout_dir, _stem(source, "item"))
        return result

    def analyze_with_cutout(self, source: ImageInput) -> tuple[AnalysisResult, Optional[Image.Image]]:
        """분석 결과와 배경 제거 이미지(RGBA)를 함께 돌려준다. 저장은 호출한 쪽에서 한다."""
        result = AnalysisResult()
        started = time.perf_counter()
        try:
            image = load_image(source)
        except Exception as error:  # 손상된 파일 등
            result.warnings.append(f"사진을 열 수 없어요: {error}")
            return result, None

        with self._lock:
            mask = self._segment(image, result)
            cutout = background.make_cutout(image, mask) if mask is not None else None
            self._colors(image, mask, result)
            self._attributes(image, cutout, result)

        self._suggest_name(result)
        result.timings_ms["전체"] = round((time.perf_counter() - started) * 1000, 1)
        return result, cutout

    # ------------------------------------------------------------ 여러 옷 사진

    def analyze_outfit(self, source: ImageInput, cutout_dir: Union[str, Path, None] = None) -> OutfitAnalysisResult:
        """옷이 여러 벌 찍힌 사진을 옷별로 나눠 분석한다.

        cutout_dir를 주면 옷마다 배경 제거 이미지를 종류별 폴더에 저장한다.
        `<cutout_dir>/<상의|하의|겉옷|신발>/<사진이름>_<번호>.png` (번호는 사진의 위에서 아래 순서)
        """
        result, cutouts = self.analyze_outfit_with_cutouts(source)
        if cutout_dir is not None:
            stem = _stem(source, "item")
            for index, (item, cutout) in enumerate(zip(result.items, cutouts), start=1):
                save_by_category(cutout, item.analysis, cutout_dir, f"{stem}_{index}")
        return result

    def analyze_outfit_with_cutouts(
        self, source: ImageInput
    ) -> tuple[OutfitAnalysisResult, list[Optional[Image.Image]]]:
        """옷별 분석 결과와, 같은 순서의 배경 제거 이미지 목록을 돌려준다."""
        result = OutfitAnalysisResult()
        started = time.perf_counter()
        try:
            image = load_image(source)
        except Exception as error:
            result.warnings.append(f"사진을 열 수 없어요: {error}")
            return result, []

        pairs: list[tuple[DetectedGarment, Optional[Image.Image]]] = []
        with self._lock:
            step = time.perf_counter()
            try:
                detections = self.detector.detect(image)
                result.models["옷 찾기"] = self.detector.model_id
            except Exception as error:
                result.warnings.append(f"사진에서 옷을 찾지 못했어요: {error}")
                return result, []
            regions, result.skipped = select_garments(detections, image.width, image.height)
            result.timings_ms["옷 찾기"] = round((time.perf_counter() - step) * 1000, 1)

            if not regions:
                result.warnings.append(
                    "사진에서 옷을 찾지 못했어요. 옷이 한 벌만 찍힌 사진이라면 한 벌 분석을 써 주세요."
                )
                result.timings_ms["전체"] = round((time.perf_counter() - started) * 1000, 1)
                return result, []

            # 배경 제거는 사진 전체에 한 번만 하고, 옷마다 자기 상자 안쪽만 쓴다.
            whole = AnalysisResult()
            mask = self._segment(image, whole, require_single_garment=False)
            result.timings_ms["배경 제거"] = whole.timings_ms.get("배경 제거", 0.0)
            result.models.update(whole.models)
            if mask is None:
                result.warnings.append("배경을 지우지 못해 색상은 비워 뒀어요. 직접 골라 주세요.")

            step = time.perf_counter()
            for region in regions:
                pairs.append(self._analyze_region(image, mask, region))
            result.timings_ms["옷별 분석"] = round((time.perf_counter() - step) * 1000, 1)
            result.models["분류"] = self.classifier.model_id

        names = [region.region for region in regions]
        dropped = layer_duplicates([item for item, _ in pairs], names)
        kept = [pair for index, pair in enumerate(pairs) if index not in dropped]
        result.items = [item for item, _ in kept]
        strip_overlapping_colors(result.items, [name for index, name in enumerate(names) if index not in dropped])
        for item in result.items:
            self._suggest_name(item.analysis)
        result.timings_ms["전체"] = round((time.perf_counter() - started) * 1000, 1)
        return result, [cutout for _, cutout in kept]

    def _analyze_region(
        self, image: Image.Image, mask: Optional[Image.Image], region: GarmentRegion
    ) -> tuple[DetectedGarment, Optional[Image.Image]]:
        def padded(box) -> tuple[int, int, int, int]:
            pad_x, pad_y = _BOX_PADDING * (box[2] - box[0]), _BOX_PADDING * (box[3] - box[1])
            return (
                max(0, int(box[0] - pad_x)),
                max(0, int(box[1] - pad_y)),
                min(image.width, int(box[2] + pad_x) + 1),
                min(image.height, int(box[3] + pad_y) + 1),
            )

        bounds = padded(region.bounds)
        crop = image.crop(bounds)
        analysis = AnalysisResult()

        region_mask: Optional[Image.Image] = None
        if mask is not None:
            # 이 옷의 상자들 안쪽만 남긴다. (신발은 두 짝 사이의 바닥·바짓단을 빼기 위해 상자별로 남긴다)
            inside = Image.new("L", image.size, 0)
            draw = ImageDraw.Draw(inside)
            for box in region.boxes:
                draw.rectangle(padded(box), fill=255)
            region_mask = ImageChops.multiply(mask, inside).crop(bounds)
            fill = float((np.asarray(region_mask) > 127).mean())
            analysis.foreground_ratio = round(fill, 4)
            if fill < _REGION_MIN_FILL:
                region_mask = None

        cutout = background.make_cutout(crop, region_mask) if region_mask is not None else None
        if region_mask is None:
            analysis.warnings.append("이 옷의 영역을 가려내지 못해 색상은 비워 뒀어요. 직접 골라 주세요.")
        else:
            self._colors(crop, region_mask, analysis)
        self._attributes(crop, cutout, analysis, allowed=region.allowed_categories)
        if len(region.allowed_categories) == 1:
            # 종류는 검출 모델이 정했으므로 확신도도 검출 점수를 쓴다.
            analysis.category.confidence = round(region.score, 4)
        self._suggest_name(analysis)
        analysis.timings_ms.clear()  # 옷별 시간은 묶어서 한 번만 보고한다

        box = region.bounds
        garment = DetectedGarment(
            box=[
                round(box[0] / image.width, 4),
                round(box[1] / image.height, 4),
                round(box[2] / image.width, 4),
                round(box[3] / image.height, 4),
            ],
            detector_label=region.label,
            detector_score=round(region.score, 4),
            analysis=analysis,
        )
        return garment, cutout

    # ------------------------------------------------------------ 단계별

    def _segment(
        self, image: Image.Image, result: AnalysisResult, require_single_garment: bool = True
    ) -> Optional[Image.Image]:
        if not self._remove_background:
            return None
        started = time.perf_counter()
        try:
            remover = self.remover
            assert remover is not None
            mask = remover.mask(image)
            result.models["배경 제거"] = remover.model_id
        except Exception as error:
            result.warnings.append(f"배경을 지우지 못했어요: {error}")
            return None
        finally:
            result.timings_ms["배경 제거"] = round((time.perf_counter() - started) * 1000, 1)

        result.foreground_ratio = round(background.foreground_ratio(mask), 4)
        if require_single_garment and not background.is_plausible_garment(mask):
            result.warnings.append("사진에서 옷을 가려내지 못했어요. 옷이 한 벌만 잘 보이게 다시 찍어 주세요.")
            return None
        return mask

    def _colors(self, image: Image.Image, mask: Optional[Image.Image], result: AnalysisResult) -> None:
        if mask is None:
            # 배경이 섞인 색을 확정처럼 보여주지 않는다.
            result.warnings.append("옷 영역을 몰라 색상은 비워 뒀어요. 직접 골라 주세요.")
            return
        started = time.perf_counter()
        try:
            result.colors = extract_colors(image, mask)
            if not result.colors:
                result.warnings.append("색상을 뽑지 못했어요. 직접 골라 주세요.")
        except Exception as error:
            result.warnings.append(f"색상을 계산하지 못했어요: {error}")
        result.timings_ms["색상"] = round((time.perf_counter() - started) * 1000, 1)

    def _attributes(
        self,
        image: Image.Image,
        cutout: Optional[Image.Image],
        result: AnalysisResult,
        allowed: Optional[Collection[Category]] = None,
    ) -> None:
        started = time.perf_counter()
        try:
            classifier = self.classifier
            use_cutout = self.classify_on == "cutout" and cutout is not None
            target = background.on_white(cutout) if use_cutout else image  # type: ignore[arg-type]
            attributes = suggest_attributes(classifier, classifier.embed(target), allowed=allowed)
            result.category = attributes.category
            result.subtype = attributes.subtype
            result.warmth = attributes.warmth
            result.style = attributes.style
            result.waterproof = attributes.waterproof
            result.grip = attributes.grip
            result.warnings.extend(attributes.warnings)
            result.models["분류"] = classifier.model_id
        except Exception as error:
            result.warnings.append(f"종류를 분석하지 못했어요. 직접 골라 주세요. ({error})")
        result.timings_ms["분류"] = round((time.perf_counter() - started) * 1000, 1)

    @staticmethod
    def _suggest_name(result: AnalysisResult) -> None:
        if result.subtype.value or result.category.value:
            color = f"{result.colors[0].name} " if result.colors else ""
            result.name_suggestion = f"{color}{result.subtype.value or result.category.value}"


_analyzer: Optional[GarmentAnalyzer] = None
_analyzer_lock = threading.Lock()


def get_analyzer() -> GarmentAnalyzer:
    """프로세스에 하나만 두는 분석기. 모델은 처음 쓸 때 메모리에 올라간다."""
    global _analyzer
    with _analyzer_lock:
        if _analyzer is None:
            _analyzer = GarmentAnalyzer()
        return _analyzer
