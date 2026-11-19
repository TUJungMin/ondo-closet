"""분류 확률을 '종류·세부 종류·보온성·스타일' 제안으로 바꾼다.

확신이 기준보다 낮으면 value를 None으로 두고 후보만 돌려준다. 틀린 값을 확정처럼 보여주지 않기 위해서다.
"""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .. import config
from ..schemas import Candidate, Category, Suggestion
from .classifier import ZeroShotClassifier
from .labels import (
    OTHER_ITEMS,
    STYLE_PROMPTS,
    SUBTYPE_PROMPTS,
    SUBTYPES,
    WARMTH_LEVELS,
    WARMTH_PROMPTS,
    Subtype,
)

_WARMTH_NAMES = ("얇음", "중간", "두꺼움")
_WARMTH_STRONG = 0.70  # 세부 종류 기본값과 반대 방향일 때 한 단계 보정하는 기준
_WARMTH_VERY_STRONG = 0.80


@dataclass
class Attributes:
    category: Suggestion
    subtype: Suggestion
    warmth: Suggestion
    style: Suggestion
    waterproof: Optional[bool] = None
    grip: Optional[bool] = None
    matched: Optional[Subtype] = None
    warnings: list[str] = field(default_factory=list)


def _top(labels: list[str], scores: np.ndarray, n: int = 3) -> list[Candidate]:
    order = np.argsort(scores)[::-1][:n]
    return [Candidate(label=labels[i], score=round(float(scores[i]), 4)) for i in order]


def _suggest_category(
    probs: np.ndarray, warnings: list[str], forced: bool = False
) -> tuple[Suggestion, Optional[Category]]:
    n = len(SUBTYPES)
    categories = list(Category)
    by_category = np.array([sum(probs[i] for i, s in enumerate(SUBTYPES) if s.category == c) for c in categories])
    other = probs[n:]
    best = int(by_category.argmax())
    confidence = float(by_category[best])
    candidates = [c for c in _top([c.value for c in categories], by_category) if c.score > 0]
    suggestion = Suggestion(confidence=round(confidence, 4), candidates=candidates)

    if forced:
        # 후보 종류가 이미 좁혀져 있다 (여러 옷 사진에서 검출 모델이 부위를 알려 준 경우).
        suggestion.value = categories[best].value
        return suggestion, categories[best]
    if other.sum() > confidence:
        guess = OTHER_ITEMS[int(other.argmax())][0]
        warnings.append(f"옷장에서 다루지 않는 종류({guess})로 보여요. 종류를 직접 골라 주세요.")
        return suggestion, None
    if confidence < config.CATEGORY_MIN_CONFIDENCE:
        warnings.append("종류를 확신하기 어려워요. 직접 골라 주세요.")
        return suggestion, None
    suggestion.value = categories[best].value
    return suggestion, categories[best]


def _suggest_subtype(probs: np.ndarray, category: Optional[Category]) -> tuple[Suggestion, Optional[Subtype]]:
    if category is None:
        return Suggestion(), None
    indices = [i for i, s in enumerate(SUBTYPES) if s.category == category]
    within = probs[indices]
    total = within.sum()
    if total <= 0:
        return Suggestion(), None
    within = within / total
    best = int(within.argmax())
    confidence = float(within[best])
    suggestion = Suggestion(
        confidence=round(confidence, 4),
        candidates=_top([SUBTYPES[i].name for i in indices], within),
    )
    if confidence < config.SUBTYPE_MIN_CONFIDENCE:
        return suggestion, None
    matched = SUBTYPES[indices[best]]
    suggestion.value = matched.name
    return suggestion, matched


def _suggest_warmth(probs: np.ndarray, matched: Optional[Subtype], subtype_conf: float) -> Suggestion:
    """세부 종류의 기본 보온성에서 출발해, 얇음/두꺼움 문구가 강하게 반대할 때만 한 단계 옮긴다."""
    thin, _, thick = (float(p) for p in probs)
    candidates = _top(list(_WARMTH_NAMES), probs)
    if matched is None:
        confidence = float(probs.max())
        if confidence < config.WARMTH_MIN_CONFIDENCE:
            return Suggestion(confidence=round(confidence, 4), candidates=candidates)
        expected = float(np.dot(probs, WARMTH_LEVELS))
        return Suggestion(value=int(round(expected)), confidence=round(confidence, 4), candidates=candidates)

    value = matched.warmth
    if matched.category != Category.SHOES:
        if (value >= 4 and thin >= _WARMTH_STRONG) or (value == 3 and thin >= _WARMTH_VERY_STRONG):
            value -= 1
        elif (value <= 2 and thick >= _WARMTH_STRONG) or (value == 3 and thick >= _WARMTH_VERY_STRONG):
            value += 1
    return Suggestion(value=value, confidence=round(subtype_conf, 4), candidates=candidates)


def _suggest_style(probs: np.ndarray, matched: Optional[Subtype], subtype_conf: float) -> Suggestion:
    names = [style.value for style, _ in STYLE_PROMPTS]
    candidates = _top(names, probs)
    best = int(probs.argmax())
    confidence = float(probs[best])
    if confidence >= config.STYLE_MIN_CONFIDENCE:
        return Suggestion(value=names[best], confidence=round(confidence, 4), candidates=candidates)
    if matched is not None:
        return Suggestion(value=matched.style.value, confidence=round(subtype_conf * 0.8, 4), candidates=candidates)
    return Suggestion(confidence=round(confidence, 4), candidates=candidates)


def _restrict(probs: np.ndarray, allowed: Collection[Category]) -> np.ndarray:
    """허용한 종류의 세부 종류만 남기고 다시 합이 1이 되게 한다."""
    keep = np.array([s.category in allowed for s in SUBTYPES] + [False] * len(OTHER_ITEMS))
    kept = np.where(keep, probs, 0.0)
    total = kept.sum()
    return kept / total if total > 0 else keep / keep.sum()


def suggest_attributes(
    classifier: ZeroShotClassifier, image_embedding, allowed: Optional[Collection[Category]] = None
) -> Attributes:
    """allowed를 주면 그 종류 안에서만 고른다. 이때는 종류를 비우지 않는다."""
    warnings: list[str] = []
    subtype_probs = classifier.probabilities(image_embedding, SUBTYPE_PROMPTS)
    if allowed:
        subtype_probs = _restrict(subtype_probs, allowed)
    category, cat = _suggest_category(subtype_probs, warnings, forced=bool(allowed))
    subtype, matched = _suggest_subtype(subtype_probs, cat)

    warmth_probs = classifier.probabilities(image_embedding, WARMTH_PROMPTS)
    style_probs = classifier.probabilities(image_embedding, [p for _, p in STYLE_PROMPTS])
    if cat is None:
        # 종류를 모르면 나머지도 제안하지 않는다.
        return Attributes(category, subtype, Suggestion(), Suggestion(), warnings=warnings)

    return Attributes(
        category=category,
        subtype=subtype,
        warmth=_suggest_warmth(warmth_probs, matched, subtype.confidence),
        style=_suggest_style(style_probs, matched, subtype.confidence),
        waterproof=matched.waterproof if matched else None,
        grip=matched.grip if matched else None,
        matched=matched,
        warnings=warnings,
    )
