"""한 장에 옷이 여러 벌인 사진(착용 사진 등)에서 옷 위치 찾기.

검출 모델(yolos-fashionpedia)은 옷뿐 아니라 소매·주머니·깃 같은 부분, 가방·모자까지 상자로 돌려준다.
여기서 옷장 다섯 종류에 해당하는 상자만 골라 '옷 한 벌' 단위로 정리한다.

이 모델은 사람이 입은 사진으로 학습됐다. 바닥에 놓고 찍은 단품 사진, 특히 신발은 잘 찾지 못하므로
단품 사진은 기존 analyze 경로를 쓴다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from PIL import Image

from .. import config
from ..config import DETECTOR, ModelSpec
from ..schemas import Category

Box = tuple[float, float, float, float]  # 왼쪽, 위, 오른쪽, 아래 (픽셀)

UPPER, LOWER, FEET = "상체", "하체", "발"

# 검출 모델의 이름 → (옷장 종류, 부위)
GARMENT_LABELS: dict[str, tuple[Category, str]] = {
    "shirt, blouse": (Category.TOP, UPPER),
    "top, t-shirt, sweatshirt": (Category.TOP, UPPER),
    "sweater": (Category.TOP, UPPER),
    "vest": (Category.TOP, UPPER),
    "cardigan": (Category.OUTER, UPPER),
    "jacket": (Category.OUTER, UPPER),
    "coat": (Category.OUTER, UPPER),
    "cape": (Category.OUTER, UPPER),
    "pants": (Category.PANTS, LOWER),
    "shorts": (Category.PANTS, LOWER),
    "skirt": (Category.SKIRT, LOWER),
    "shoe": (Category.SHOES, FEET),
}

# 찾기는 했지만 옷장 종류가 아니라 빼는 것
SKIPPED_LABELS: dict[str, str] = {
    "dress": "원피스",
    "jumpsuit": "점프수트",
    "bag, wallet": "가방",
    "hat": "모자",
    "scarf": "목도리",
}

# 부위별로 분류 모델이 고를 수 있는 종류. 상체는 상의·겉옷 구분을 분류 모델에 맡긴다.
# (후드티를 검출 모델이 jacket으로 부르는 일이 있어서다.) 하체·발은 검출 모델의 판단을 따른다.
UPPER_CATEGORIES = frozenset((Category.TOP, Category.OUTER))


@dataclass(frozen=True)
class Detection:
    label: str
    score: float
    box: Box


@dataclass
class GarmentRegion:
    """옷 한 벌에 해당하는 영역. 신발은 좌우 두 짝을 한 벌로 묶으므로 상자가 여러 개일 수 있다."""

    region: str
    category: Category
    label: str
    score: float
    boxes: list[Box] = field(default_factory=list)

    @property
    def bounds(self) -> Box:
        return (
            min(b[0] for b in self.boxes),
            min(b[1] for b in self.boxes),
            max(b[2] for b in self.boxes),
            max(b[3] for b in self.boxes),
        )

    @property
    def allowed_categories(self) -> frozenset[Category]:
        return UPPER_CATEGORIES if self.region == UPPER else frozenset((self.category,))


def area(box: Box) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def _intersection(a: Box, b: Box) -> float:
    return area((max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])))


def iou(a: Box, b: Box) -> float:
    inter = _intersection(a, b)
    union = area(a) + area(b) - inter
    return inter / union if union > 0 else 0.0


def contained(inner: Box, outer: Box) -> float:
    """inner 넓이 중 outer 안에 들어 있는 비율."""
    inner_area = area(inner)
    return _intersection(inner, outer) / inner_area if inner_area > 0 else 0.0


def select_garments(
    detections: Sequence[Detection], width: int, height: int
) -> tuple[list[GarmentRegion], list[str]]:
    """검출 결과에서 옷 한 벌 단위의 영역을 고른다. (영역 목록, 뺀 것 이름 목록)을 돌려준다.

    - 점수가 낮거나 너무 작은 상자는 버린다
    - 같은 부위에서 많이 겹치는 상자는 점수가 높은 것만 남긴다 (한 옷이 두 이름으로 잡힌 경우)
    - 같은 종류의 상자 안에 든 작은 상자는 버린다 (바지의 일부만 다시 잡힌 경우)
    - 신발은 찾은 상자를 모두 묶어 한 벌로 본다
    결과는 사진의 위에서 아래 순서다.
    """
    image_area = float(width * height)
    regions: list[GarmentRegion] = []
    shoes: list[Detection] = []
    skipped: list[str] = []

    for det in sorted(detections, key=lambda d: d.score, reverse=True):
        if det.score < config.DETECT_MIN_SCORE:
            continue
        if det.label in SKIPPED_LABELS:
            if SKIPPED_LABELS[det.label] not in skipped:
                skipped.append(SKIPPED_LABELS[det.label])
            continue
        if det.label not in GARMENT_LABELS:
            continue  # 소매·주머니·깃 같은 옷의 부분

        box = (max(0.0, det.box[0]), max(0.0, det.box[1]), min(float(width), det.box[2]), min(float(height), det.box[3]))
        category, region = GARMENT_LABELS[det.label]
        share = area(box) / image_area
        if region == FEET:
            if share >= config.DETECT_MIN_SHOE_AREA:
                shoes.append(Detection(det.label, det.score, box))
            continue
        if share < config.DETECT_MIN_GARMENT_AREA:
            continue
        duplicate = any(
            kept.region == region
            and (
                iou(box, kept.boxes[0]) >= config.DETECT_DUPLICATE_IOU
                or (kept.category == category and contained(box, kept.boxes[0]) >= config.DETECT_CONTAINED)
            )
            for kept in regions
        )
        if not duplicate:
            regions.append(GarmentRegion(region, category, det.label, det.score, [box]))

    if shoes:
        regions.append(
            GarmentRegion(FEET, Category.SHOES, "shoe", max(s.score for s in shoes), [s.box for s in shoes])
        )
    regions.sort(key=lambda r: r.bounds[1])
    return regions, skipped


class GarmentDetector:
    """yolos-fashionpedia. transformers에 들어 있는 YOLOS 구조라 원격 코드를 실행하지 않는다."""

    def __init__(self, device: str, spec: ModelSpec = DETECTOR):
        import torch
        from transformers import AutoImageProcessor, AutoModelForObjectDetection

        self._torch = torch
        self._device = device
        self._processor = AutoImageProcessor.from_pretrained(spec.repo_id, revision=spec.revision)
        model = AutoModelForObjectDetection.from_pretrained(spec.repo_id, revision=spec.revision)
        self._model = model.to(device).float().eval()
        self._labels: dict[int, str] = self._model.config.id2label
        self.model_id = f"{spec.repo_id}@{spec.revision[:8]}"

    def detect(self, image: Image.Image, min_score: float = 0.30) -> list[Detection]:
        """사진에서 찾은 모든 상자. 옷으로 쓸지는 select_garments가 정한다."""
        torch = self._torch
        inputs = self._processor(images=image.convert("RGB"), return_tensors="pt").to(self._device)
        with torch.inference_mode():
            outputs = self._model(**inputs)
        found = self._processor.post_process_object_detection(
            outputs, threshold=min_score, target_sizes=[(image.height, image.width)]
        )[0]
        return [
            Detection(self._labels[int(label)], float(score), tuple(float(v) for v in box))  # type: ignore[arg-type]
            for score, label, box in zip(found["scores"].tolist(), found["labels"].tolist(), found["boxes"].tolist())
        ]
