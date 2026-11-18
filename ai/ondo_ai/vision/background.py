"""배경 제거. ZhengPeng7/BiRefNet으로 옷 영역 마스크를 구한다.

모델 카드 예제대로 1024×1024 입력, ImageNet 정규화를 쓴다. GPU에서는 half precision으로 돌린다.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
from PIL import Image

from .. import config
from ..config import SEGMENTER, ModelSpec

_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


class BiRefNetRemover:
    def __init__(self, device: str, spec: ModelSpec = SEGMENTER, size: Optional[int] = None):
        import torch
        from transformers import AutoModelForImageSegmentation

        self._torch = torch
        self._device = device
        self._size = size or config.SEGMENT_SIZE
        self._half = device.startswith("cuda")
        model = AutoModelForImageSegmentation.from_pretrained(
            spec.repo_id, revision=spec.revision, trust_remote_code=True
        )
        model = model.to(device).eval()
        # 저장된 가중치가 half precision이라, 최신 transformers에서는 그대로 half로 올라온다.
        # CPU는 half 연산을 지원하지 않으므로 명시적으로 float32로 바꾼다.
        self._model = model.half() if self._half else model.float()
        self.model_id = f"{spec.repo_id}@{spec.revision[:8]}"

    def mask(self, image: Image.Image) -> Image.Image:
        """옷(전경)이 밝은 'L' 마스크를 원본 크기로 돌려준다."""
        torch = self._torch
        resized = image.convert("RGB").resize((self._size, self._size), Image.BILINEAR)
        array = (np.asarray(resized, dtype=np.float32) / 255.0 - _MEAN) / _STD
        tensor = torch.from_numpy(array.transpose(2, 0, 1)).unsqueeze(0).to(self._device)
        if self._half:
            tensor = tensor.half()
        with torch.inference_mode():
            prediction = self._model(tensor)[-1].sigmoid().float().cpu()[0, 0].numpy()
        mask = Image.fromarray((prediction * 255).astype(np.uint8), mode="L")
        return mask.resize(image.size, Image.BILINEAR)


def foreground_ratio(mask: Image.Image) -> float:
    return float((np.asarray(mask) > 127).mean())


def is_plausible_garment(mask: Image.Image) -> bool:
    """마스크가 옷 한 벌처럼 생겼는지.

    너무 작거나 사진 전체를 덮으면 실패로 본다. 또 옷 둘레 상자 안이 거의 비어 있으면
    (윤곽선만 잡힌 경우 등) 옷 면적이 아니라 테두리만 잡힌 것이므로 실패로 본다.
    """
    binary = np.asarray(mask) > 127
    ratio = float(binary.mean())
    if not (config.FOREGROUND_MIN_RATIO <= ratio <= config.FOREGROUND_MAX_RATIO):
        return False
    rows, cols = np.where(binary.any(axis=1))[0], np.where(binary.any(axis=0))[0]
    box_area = (rows[-1] - rows[0] + 1) * (cols[-1] - cols[0] + 1)
    return float(binary.sum()) / float(box_area) >= config.FOREGROUND_MIN_FILL


def make_cutout(image: Image.Image, mask: Image.Image, max_side: Optional[int] = None) -> Image.Image:
    """마스크를 알파로 붙이고 옷 둘레로 잘라낸 RGBA 이미지. 옷장 격자 표시에 쓴다."""
    rgba = image.convert("RGB").copy()
    rgba.putalpha(mask)
    box = mask.point(lambda v: 255 if v > 127 else 0).getbbox()
    if box is not None:
        pad = int(0.04 * max(box[2] - box[0], box[3] - box[1]))
        box = (
            max(0, box[0] - pad),
            max(0, box[1] - pad),
            min(image.width, box[2] + pad),
            min(image.height, box[3] + pad),
        )
        rgba = rgba.crop(box)
    max_side = max_side or config.CUTOUT_MAX_SIDE
    if max(rgba.size) > max_side:
        rgba.thumbnail((max_side, max_side), Image.LANCZOS)
    return rgba


def on_white(cutout: Image.Image) -> Image.Image:
    """RGBA 이미지를 흰 바탕 정사각형 가운데에 올린다. (분류 모델이 비율을 찌그러뜨리지 않게)"""
    side = max(cutout.size)
    canvas = Image.new("RGB", (side, side), (255, 255, 255))
    canvas.paste(cutout, ((side - cutout.width) // 2, (side - cutout.height) // 2), cutout)
    return canvas
