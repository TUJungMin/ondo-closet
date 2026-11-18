"""제로샷 분류기. 사진 임베딩과 후보 문구 임베딩의 유사도를 확률로 바꾼다.

기본 모델은 Marqo/marqo-fashionSigLIP이다. 모델 카드가 안내하는 두 경로(AutoModel, OpenCLIP) 중
OpenCLIP 경로로 불러온다: AutoModel 래퍼는 transformers 5.x에서 'Cannot copy out of meta tensor'
오류로 로드되지 않는 것을 확인했다(2026-11-18, transformers 5.23.0). 가중치는 같은 저장소의 같은 것이다.
"""

from __future__ import annotations

from typing import Protocol, Sequence

import numpy as np
from PIL import Image

from ..config import BASELINE_CLASSIFIER, CLASSIFIER, ModelSpec

_LOGIT_SCALE = 100.0  # 모델 카드 예제와 같은 값


class EmbeddingBackend(Protocol):
    model_id: str

    def encode_text(self, texts: Sequence[str]): ...  # (N, D) 정규화된 텐서

    def encode_image(self, image: Image.Image): ...  # (1, D) 정규화된 텐서


class FashionSigLIPBackend:
    """Marqo/marqo-fashionSigLIP (OpenCLIP 형식 가중치)."""

    def __init__(self, device: str, spec: ModelSpec = CLASSIFIER):
        import open_clip
        import torch
        from huggingface_hub import snapshot_download

        # 고정한 리비전에서 필요한 파일만 받는다. (같은 저장소의 ONNX 등은 받지 않음)
        local_dir = snapshot_download(
            spec.repo_id,
            revision=spec.revision,
            allow_patterns=[
                "open_clip_config.json",
                "open_clip_model.safetensors",
                "tokenizer.json",
                "tokenizer_config.json",
                "special_tokens_map.json",
                "spiece.model",
            ],
        )
        source = f"local-dir:{local_dir}"
        model, _, preprocess = open_clip.create_model_and_transforms(source)
        self._torch = torch
        self._model = model.to(device).float().eval()
        self._preprocess = preprocess
        self._tokenizer = open_clip.get_tokenizer(source)
        self._device = device
        self.model_id = f"{spec.repo_id}@{spec.revision[:8]}"

    def encode_text(self, texts: Sequence[str]):
        with self._torch.inference_mode():
            tokens = self._tokenizer(list(texts)).to(self._device)
            return self._model.encode_text(tokens, normalize=True).float()

    def encode_image(self, image: Image.Image):
        with self._torch.inference_mode():
            pixels = self._preprocess(image.convert("RGB")).unsqueeze(0).to(self._device)
            return self._model.encode_image(pixels, normalize=True).float()


class FashionCLIPBackend:
    """patrickjohncyh/fashion-clip. 평가에서 비교 기준선으로만 쓴다."""

    def __init__(self, device: str, spec: ModelSpec = BASELINE_CLASSIFIER):
        import torch
        from transformers import CLIPModel, CLIPProcessor

        self._torch = torch
        self._model = CLIPModel.from_pretrained(spec.repo_id, revision=spec.revision).to(device).float().eval()
        self._processor = CLIPProcessor.from_pretrained(spec.repo_id, revision=spec.revision)
        self._device = device
        self.model_id = spec.repo_id

    def _features(self, output):
        # transformers 버전에 따라 텐서 또는 출력 객체가 온다.
        feats = output if self._torch.is_tensor(output) else output.pooler_output
        return self._torch.nn.functional.normalize(feats.float(), dim=-1)

    def encode_text(self, texts: Sequence[str]):
        with self._torch.inference_mode():
            inputs = self._processor(text=list(texts), return_tensors="pt", padding=True).to(self._device)
            return self._features(self._model.get_text_features(**inputs))

    def encode_image(self, image: Image.Image):
        with self._torch.inference_mode():
            inputs = self._processor(images=image.convert("RGB"), return_tensors="pt").to(self._device)
            return self._features(self._model.get_image_features(**inputs))


class ZeroShotClassifier:
    """문구 묶음별 텍스트 임베딩을 캐시해 두고, 사진마다 이미지 인코딩 한 번으로 여러 속성을 뽑는다."""

    def __init__(self, backend: EmbeddingBackend):
        self.backend = backend
        self._text_cache: dict[tuple[str, ...], object] = {}

    @property
    def model_id(self) -> str:
        return self.backend.model_id

    def embed(self, image: Image.Image):
        return self.backend.encode_image(image)

    def probabilities(self, image_embedding, prompts: Sequence[str]) -> np.ndarray:
        key = tuple(prompts)
        if key not in self._text_cache:
            self._text_cache[key] = self.backend.encode_text(key)
        text = self._text_cache[key]
        logits = _LOGIT_SCALE * image_embedding @ text.T  # type: ignore[union-attr]
        return logits.softmax(dim=-1)[0].cpu().numpy().astype(np.float64)


def build_classifier(device: str, model: str = "fashion-siglip") -> ZeroShotClassifier:
    if model == "fashion-siglip":
        return ZeroShotClassifier(FashionSigLIPBackend(device))
    if model == "fashion-clip":
        return ZeroShotClassifier(FashionCLIPBackend(device))
    raise ValueError(f"알 수 없는 분류 모델: {model}")
