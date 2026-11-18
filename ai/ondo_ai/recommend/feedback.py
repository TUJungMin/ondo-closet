"""거절 이유와 착용 기록을 점수 조정값으로 바꾼다."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Optional, Sequence

from ..palette import pair_harmony
from ..schemas import Category, Garment, Place, RejectReason, Rejection, Style, WearRecord
from .thermal import OffsetEstimate, estimate_offset, recency_weight

_REJECT_HALF_LIFE_DAYS = 30.0
_MAIN = (Category.TOP, Category.PANTS, Category.SKIRT, Category.OUTER)


def outfit_key(item_ids: Sequence) -> frozenset[str]:
    return frozenset(str(i) for i in item_ids)


def color_key(a: str, b: str) -> frozenset[str]:
    return frozenset((a, b))


@dataclass
class Learned:
    offset: OffsetEstimate = field(default_factory=OffsetEstimate)
    # '색이 안 맞음': 색 쌍별 감점 세기
    color_pairs: dict[frozenset[str], float] = field(default_factory=dict)
    # '장소에 안 맞음': (옷, 장소) / (스타일, 장소) 감점 세기
    item_place: dict[tuple[str, Place], float] = field(default_factory=dict)
    style_place: dict[tuple[Style, Place], float] = field(default_factory=dict)
    # 거절한 조합 그대로 다시 나오지 않게
    rejected_outfits: dict[frozenset[str], float] = field(default_factory=dict)
    # '직접 입력': 같은 옷을 고정했을 때 함께 나왔던 옷 소폭 감점. 키는 (고정 옷, 옷)
    soft_items: dict[tuple[str, str], float] = field(default_factory=dict)
    # 만족도 기록: 옷별 -1..1
    satisfaction: dict[str, float] = field(default_factory=dict)
    recently_worn: set[str] = field(default_factory=set)
    reject_counts: dict[RejectReason, int] = field(default_factory=dict)


def _primary(g: Garment) -> Optional[str]:
    return g.colors[0] if g.colors else None


def learn(
    wear_history: Sequence[WearRecord],
    rejections: Sequence[Rejection],
    by_id: dict[str, Garment],
    today: dt.date,
) -> Learned:
    learned = Learned(offset=estimate_offset(wear_history, rejections, by_id, today))

    for rej in rejections:
        w = recency_weight(rej.date, today, _REJECT_HALF_LIFE_DAYS)
        learned.reject_counts[rej.reason] = learned.reject_counts.get(rej.reason, 0) + 1
        key = outfit_key(rej.item_ids)
        learned.rejected_outfits[key] = max(learned.rejected_outfits.get(key, 0.0), w)

        items = [by_id[str(i)] for i in rej.item_ids if str(i) in by_id]
        pinned_key = str(rej.pinned_id) if rej.pinned_id is not None else None
        others = [g for g in items if str(g.id) != pinned_key]

        if rej.reason == RejectReason.COLOR:
            _learn_color(learned, items, by_id.get(pinned_key or ""), w)
        elif rej.reason == RejectReason.PLACE and rej.place is not None:
            for g in others:
                k = (str(g.id), rej.place)
                learned.item_place[k] = learned.item_place.get(k, 0.0) + w
            for style in {g.style for g in others if g.style is not None}:
                k2 = (style, rej.place)
                learned.style_place[k2] = learned.style_place.get(k2, 0.0) + 0.5 * w
        elif rej.reason == RejectReason.OTHER and pinned_key is not None:
            for g in others:
                k3 = (pinned_key, str(g.id))
                learned.soft_items[k3] = learned.soft_items.get(k3, 0.0) + w

    sat_sum: dict[str, float] = {}
    sat_w: dict[str, float] = {}
    for rec in wear_history:
        if (today - rec.date).days in (0, 1):
            learned.recently_worn.update(str(i) for i in rec.item_ids)
        if rec.satisfaction is None:
            continue
        w = recency_weight(rec.date, today, _REJECT_HALF_LIFE_DAYS)
        for i in rec.item_ids:
            sat_sum[str(i)] = sat_sum.get(str(i), 0.0) + w * (rec.satisfaction - 3) / 2.0
            sat_w[str(i)] = sat_w.get(str(i), 0.0) + w
    learned.satisfaction = {k: sat_sum[k] / sat_w[k] for k in sat_sum}
    return learned


def _learn_color(learned: Learned, items: list[Garment], pinned: Optional[Garment], weight: float) -> None:
    """어느 색 쌍이 문제였는지는 알 수 없으므로, 규칙상 덜 어울리는 쌍에 더 많이 책임을 나눈다."""
    main = [g for g in items if g.category in _MAIN and _primary(g)]
    if pinned is not None and _primary(pinned):
        pairs = [(pinned, g) for g in main if g.id != pinned.id]
    else:
        pairs = [(a, b) for idx, a in enumerate(main) for b in main[idx + 1 :]]
    if not pairs:
        return
    blame = [1.05 - pair_harmony(_primary(a), _primary(b))[0] for a, b in pairs]
    total = sum(blame)
    for (a, b), share in zip(pairs, blame):
        k = color_key(_primary(a), _primary(b))  # type: ignore[arg-type]
        learned.color_pairs[k] = learned.color_pairs.get(k, 0.0) + weight * share / total
