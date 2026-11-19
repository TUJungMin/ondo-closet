"""모델과 기준값 설정. 환경 변수로 덮어쓸 수 있는 값은 ONDO_ 로 시작한다."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    repo_id: str
    revision: str  # 제출 이후에도 같은 결과가 나오도록 커밋 해시로 고정한다
    license: str


# 종류·보온성·스타일 제로샷 분류
CLASSIFIER = ModelSpec("Marqo/marqo-fashionSigLIP", "c56244cc94f92419e8369fa71efdaf403b124ce8", "Apache-2.0")
# 배경 제거
SEGMENTER = ModelSpec("ZhengPeng7/BiRefNet", "e2bf8e4460fc8fa32bba5ea4d94b3233d367b0e4", "MIT")
# 한 장에 옷이 여러 벌인 사진(착용 사진 등)에서 옷 위치 찾기.
# CLAUDE.md에는 valentinafeve/yolos-fashionpedia로 적혀 있다. 저장소 주인의 계정명이 바뀌어
# Hugging Face가 아래 이름으로 넘겨 준다. 같은 저장소다. (2026-11-18 확인)
DETECTOR = ModelSpec("valentinafevu/yolos-fashionpedia", "0cfdb77c01cfbf0838b940ecff9c572f84c9d4f4", "MIT")
# 평가 때만 쓰는 비교 기준선
BASELINE_CLASSIFIER = ModelSpec("patrickjohncyh/fashion-clip", "7e3ba62ce16b379a1ab479346b66f192e76f51b7", "MIT")

# 장치: auto(기본) · cuda · cpu
DEVICE = os.environ.get("ONDO_DEVICE", "auto")
# BiRefNet 입력 한 변 길이. 모델 예제 기준은 1024. CPU에서 느리면 줄여 본다.
SEGMENT_SIZE = int(os.environ.get("ONDO_SEGMENT_SIZE", "1024"))
# 분석 전에 원본을 이 크기 이하로 줄인다 (휴대폰 원본 4000px대 대비)
MAX_IMAGE_SIDE = int(os.environ.get("ONDO_MAX_IMAGE_SIDE", "1600"))
# 저장하는 배경 제거 이미지의 최대 한 변
CUTOUT_MAX_SIDE = int(os.environ.get("ONDO_CUTOUT_MAX_SIDE", "800"))
# 분류에 넣는 이미지: cutout(배경 지운 뒤 흰 바탕) · original
CLASSIFY_ON = os.environ.get("ONDO_CLASSIFY_ON", "cutout")

# 이 값보다 확신이 낮으면 값을 비워 두고 사용자가 고르게 한다. (ai/docs/eval.md 평가 후 조정)
CATEGORY_MIN_CONFIDENCE = 0.50
SUBTYPE_MIN_CONFIDENCE = 0.40
STYLE_MIN_CONFIDENCE = 0.60
WARMTH_MIN_CONFIDENCE = 0.60

# 옷 영역이 사진의 이 범위를 벗어나면 배경 제거 실패로 본다
FOREGROUND_MIN_RATIO = 0.02
FOREGROUND_MAX_RATIO = 0.97
# 옷 둘레 상자 안에서 옷이 차지하는 비율이 이보다 낮으면 (윤곽선만 잡힌 경우 등) 실패로 본다
FOREGROUND_MIN_FILL = 0.15

# 두 번째 대표색으로 인정하는 최소 비율
SECOND_COLOR_MIN_RATIO = 0.15

# ---- 여러 옷 사진에서 옷 찾기 ----
# 이 점수 이상인 검출만 옷으로 본다
DETECT_MIN_SCORE = 0.50
# 사진 넓이 대비 상자 넓이가 이보다 작으면 버린다 (허리띠 부분만 잡힌 '상의' 같은 오검출)
DETECT_MIN_GARMENT_AREA = 0.03
DETECT_MIN_SHOE_AREA = 0.002
# 같은 부위의 두 상자가 이만큼 겹치면 같은 옷으로 본다
DETECT_DUPLICATE_IOU = 0.60
# 한 상자가 다른 상자 안에 이만큼 들어가 있으면 '안에 든 상자'로 본다
DETECT_CONTAINED = 0.80


def resolve_device(device: str | None = None) -> str:
    device = device or DEVICE
    if device != "auto":
        return device
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"
