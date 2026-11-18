"""한 벌 고정 코디 추천 (규칙 + 점수).

흐름: 입을 수 없는 옷 제외 → 고정 옷을 뺀 슬롯을 조합 → 다섯 항목으로 점수 → 서로 다른 조합 위주로 상위 k개.
점수 항목과 가중치는 아래 WEIGHTS에 모아 두었다. 추천마다 한 줄 이유와 근거 목록을 함께 돌려준다.
"""

from __future__ import annotations

import datetime as dt
import itertools
from dataclasses import dataclass, field
from typing import Optional

from ..palette import is_point_color, pair_harmony
from ..schemas import (
    SLOT_OF,
    Basis,
    Category,
    ExcludedGarment,
    Garment,
    OutfitItem,
    Place,
    Recommendation,
    RecommendContext,
    RecommendRequest,
    RecommendResult,
    RejectReason,
    Sky,
    Status,
    Style,
)
from ..text import josa
from . import thermal
from .feedback import Learned, color_key, learn, outfit_key

WEIGHTS = {"보온": 0.35, "색": 0.22, "스타일·장소": 0.20, "날씨 대비": 0.13, "선호": 0.10}
# 비·눈 오는 날은 신발·겉옷의 날씨 대비를 더 크게 본다.
WEIGHTS_BAD_WEATHER = {"보온": 0.33, "색": 0.18, "스타일·장소": 0.18, "날씨 대비": 0.22, "선호": 0.09}

_REJECTED_OUTFIT_PENALTY = 25.0  # 거절한 조합 그대로일 때 깎는 점수
_PLACE_MISFIT = 0.2  # 장소 적합도가 이 이하면 '전혀 안 맞는 옷'
_PLACE_MISFIT_PENALTY = 6.0  # 그런 옷 한 벌마다 깎는 점수
_DIVERSITY_PENALTY = 12.0  # 이미 뽑은 추천과 겹칠수록 깎는 점수
_WET_PROB = 0.6
_DIURNAL_C = 10.0

SLOT_TOP, SLOT_BOTTOM, SLOT_OUTER, SLOT_SHOES = "상의", "하의", "겉옷", "신발"
_SLOT_OF = SLOT_OF

# 장소별로 어울리는 스타일 (0~1)
_PLACE_STYLE: dict[Place, dict[Style, float]] = {
    Place.DAILY: {Style.CASUAL: 1.0, Style.FORMAL: 0.5, Style.SPORTY: 0.7, Style.STREET: 0.9, Style.FEMININE: 0.8},
    Place.OFFICE: {Style.CASUAL: 0.6, Style.FORMAL: 1.0, Style.SPORTY: 0.2, Style.STREET: 0.4, Style.FEMININE: 0.7},
    Place.FORMAL: {Style.CASUAL: 0.2, Style.FORMAL: 1.0, Style.SPORTY: 0.0, Style.STREET: 0.1, Style.FEMININE: 0.7},
    Place.DATE: {Style.CASUAL: 0.8, Style.FORMAL: 0.7, Style.SPORTY: 0.3, Style.STREET: 0.7, Style.FEMININE: 1.0},
    Place.OUTDOOR: {Style.CASUAL: 0.9, Style.FORMAL: 0.2, Style.SPORTY: 1.0, Style.STREET: 0.7, Style.FEMININE: 0.4},
    Place.SPORT: {Style.CASUAL: 0.5, Style.FORMAL: 0.0, Style.SPORTY: 1.0, Style.STREET: 0.5, Style.FEMININE: 0.1},
}
_UNKNOWN_STYLE_FIT = 0.6

# 스타일끼리 섞였을 때 어울림 (0~1). 없는 쌍은 0.5
_STYLE_MIX: dict[frozenset[Style], float] = {
    frozenset((Style.CASUAL, Style.STREET)): 0.8,
    frozenset((Style.CASUAL, Style.SPORTY)): 0.7,
    frozenset((Style.CASUAL, Style.FEMININE)): 0.7,
    frozenset((Style.CASUAL, Style.FORMAL)): 0.55,
    frozenset((Style.FORMAL, Style.FEMININE)): 0.75,
    frozenset((Style.FORMAL, Style.SPORTY)): 0.2,
    frozenset((Style.FORMAL, Style.STREET)): 0.3,
    frozenset((Style.SPORTY, Style.STREET)): 0.8,
    frozenset((Style.SPORTY, Style.FEMININE)): 0.3,
    frozenset((Style.STREET, Style.FEMININE)): 0.5,
}


@dataclass
class _Ctx:
    place: Place
    apparent: float
    effective: float
    wet: bool
    snowy: bool
    diurnal: Optional[float]
    learned: Learned
    pinned: Garment


@dataclass
class _Candidate:
    top: Optional[Garment]
    bottom: Optional[Garment]
    outer: Optional[Garment]
    shoes: Optional[Garment]
    score: float = 0.0
    parts: dict[str, float] = field(default_factory=dict)
    warmth_index: float = 0.0
    color_relation: str = "unknown"
    color_partner: Optional[Garment] = None
    diurnal_bonus: bool = False
    was_rejected: bool = False
    place_misfits: int = 0

    def items(self) -> list[Garment]:
        return [g for g in (self.top, self.bottom, self.outer, self.shoes) if g is not None]

    def ids(self) -> frozenset[str]:
        return outfit_key(g.id for g in self.items())


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _mean(values: list[float], default: float) -> float:
    return sum(values) / len(values) if values else default


def _primary(g: Optional[Garment]) -> Optional[str]:
    return g.colors[0] if (g is not None and g.colors) else None


def _is_pinned(g: Optional[Garment], ctx: _Ctx) -> bool:
    return g is not None and str(g.id) == str(ctx.pinned.id)


# ------------------------------------------------------------------ 점수 항목


def _score_warmth(c: _Candidate, ctx: _Ctx) -> float:
    t = ctx.effective
    c.warmth_index = thermal.outfit_warmth(c.top, c.bottom, c.outer)
    total_fit = thermal.gaussian_fit(c.warmth_index, thermal.target_warmth(t), 1.8)

    # 고정한 옷은 사용자가 정한 것이므로 슬롯별 적합도에서는 빼고, 나머지 옷이 전체 보온으로 맞춘다.
    slot_fits: list[float] = []
    if c.top and not _is_pinned(c.top, ctx):
        slot_fits.append(thermal.gaussian_fit(thermal.warmth_of(c.top), thermal.ideal_top(t), 1.5))
    if c.bottom and not _is_pinned(c.bottom, ctx):
        slot_fits.append(thermal.gaussian_fit(thermal.warmth_of(c.bottom), thermal.ideal_bottom(t), 1.5))
    if not _is_pinned(c.outer, ctx):
        slot_fits.append(thermal.gaussian_fit(thermal.warmth_of(c.outer), thermal.ideal_outer(t), 1.5))
    score = 0.6 * total_fit + 0.4 * _mean(slot_fits, total_fit)

    # 일교차가 큰 날은 벗기 쉬운 얇은 겉옷을 조금 더 쳐 준다.
    if (
        ctx.diurnal is not None
        and ctx.diurnal >= _DIURNAL_C
        and c.outer is not None
        and thermal.warmth_of(c.outer) <= 3
        and 14.0 < t < thermal.NO_OUTER_ABOVE_C
    ):
        c.diurnal_bonus = True
        score += 0.08
    return _clamp(score)


def _pair_score(a: Optional[Garment], b: Optional[Garment], ctx: _Ctx) -> tuple[float, str]:
    ca, cb = _primary(a), _primary(b)
    score, relation = pair_harmony(ca, cb)
    if ca and cb:
        score -= 0.5 * ctx.learned.color_pairs.get(color_key(ca, cb), 0.0)
    return _clamp(score), relation


def _score_color(c: _Candidate, ctx: _Ctx) -> float:
    main = [g for g in (c.top, c.bottom, c.outer) if g is not None]
    others = [g for g in c.items() if not _is_pinned(g, ctx)]

    with_pinned: list[tuple[float, float]] = []  # (점수, 가중치)
    for g in others:
        s, _ = _pair_score(ctx.pinned, g, ctx)
        with_pinned.append((s, 0.5 if g.category == Category.SHOES else 1.0))
    wsum = sum(w for _, w in with_pinned)
    pinned_score = sum(s * w for s, w in with_pinned) / wsum if wsum else 0.8

    among = [
        _pair_score(a, b, ctx)[0]
        for a, b in itertools.combinations(main, 2)
        if not _is_pinned(a, ctx) and not _is_pinned(b, ctx)
    ]
    among_score = _mean(among, pinned_score)

    points = {_primary(g) for g in main if is_point_color(_primary(g))}
    overall = {0: 0.9, 1: 1.0, 2: 0.6}.get(len(points), 0.25)

    # 이유 문장에 쓸 '고정 옷의 짝': 고정이 상의면 하의, 그 외에는 상의를 우선한다.
    order = (c.bottom, c.top, c.outer, c.shoes) if _is_pinned(c.top, ctx) else (c.top, c.bottom, c.outer, c.shoes)
    c.color_partner = next((g for g in order if g is not None and not _is_pinned(g, ctx)), None)
    c.color_relation = pair_harmony(_primary(ctx.pinned), _primary(c.color_partner))[1]

    return _clamp(0.45 * pinned_score + 0.25 * among_score + 0.30 * overall)


def _place_fit(g: Garment, ctx: _Ctx) -> float:
    fit = _PLACE_STYLE[ctx.place].get(g.style, _UNKNOWN_STYLE_FIT) if g.style else _UNKNOWN_STYLE_FIT
    fit -= 0.35 * ctx.learned.item_place.get((str(g.id), ctx.place), 0.0)
    if g.style:
        fit -= 0.15 * ctx.learned.style_place.get((g.style, ctx.place), 0.0)
    return _clamp(fit)


def _style_mix(a: Optional[Style], b: Optional[Style]) -> float:
    if a is None or b is None:
        return 0.65
    if a == b:
        return 1.0
    return _STYLE_MIX.get(frozenset((a, b)), 0.5)


def _score_style(c: _Candidate, ctx: _Ctx) -> float:
    others = [g for g in c.items() if not _is_pinned(g, ctx)]
    fits = [_place_fit(g, ctx) for g in others]
    # 운동에 셔츠, 격식 자리에 운동복처럼 장소에 전혀 안 맞는 옷은 평균에 묻히지 않게 따로 센다.
    c.place_misfits = sum(1 for fit in fits if fit <= _PLACE_MISFIT)
    mix = _mean([_style_mix(ctx.pinned.style, g.style) for g in others], 1.0)
    return _clamp(0.6 * _mean(fits, 1.0) + 0.4 * mix)


def _score_gear(c: _Candidate, ctx: _Ctx) -> float:
    """날씨·장소에 맞는 신발과 겉옷인지. 신발 70%, 겉옷 30%."""
    shoes_score: Optional[float] = None
    if c.shoes is not None:
        if ctx.snowy:
            condition = (1.0 if c.shoes.grip else 0.3) * (1.0 if c.shoes.waterproof else 0.8)
        elif ctx.wet:
            condition = 1.0 if c.shoes.waterproof else 0.35
        elif ctx.place in (Place.OUTDOOR, Place.SPORT):
            condition = 1.0 if c.shoes.grip else 0.6
        else:
            # 맑은 날 평소 외출에는 레인부츠 같은 방수 신발을 굳이 고르지 않는다.
            condition = 0.7 if c.shoes.waterproof else 1.0
        warmth_fit = thermal.gaussian_fit(thermal.warmth_of(c.shoes), thermal.ideal_shoes(ctx.effective), 1.5)
        shoes_score = 0.6 * condition + 0.4 * warmth_fit

    outer_score: Optional[float] = None
    if c.outer is not None and (ctx.wet or ctx.snowy):
        outer_score = 1.0 if c.outer.waterproof else 0.6

    if shoes_score is not None and outer_score is not None:
        return _clamp(0.7 * shoes_score + 0.3 * outer_score)
    if shoes_score is not None:
        return _clamp(shoes_score)
    return _clamp(outer_score if outer_score is not None else 0.7)


def _score_preference(c: _Candidate, ctx: _Ctx) -> float:
    others = [g for g in c.items() if not _is_pinned(g, ctx)]
    if not others:
        return 0.5
    learned = ctx.learned
    favorite = _mean([1.0 if g.favorite else 0.0 for g in others], 0.0)
    satisfaction = _mean([learned.satisfaction.get(str(g.id), 0.0) for g in others], 0.0)
    recent = _mean([1.0 if str(g.id) in learned.recently_worn else 0.0 for g in others], 0.0)
    soft = sum(learned.soft_items.get((str(ctx.pinned.id), str(g.id)), 0.0) for g in others)
    return _clamp(0.5 + 0.3 * favorite + 0.2 * satisfaction - 0.25 * recent - 0.1 * soft)


def _score(c: _Candidate, ctx: _Ctx) -> None:
    c.parts = {
        "보온": _score_warmth(c, ctx),
        "색": _score_color(c, ctx),
        "스타일·장소": _score_style(c, ctx),
        "날씨 대비": _score_gear(c, ctx),
        "선호": _score_preference(c, ctx),
    }
    weights = WEIGHTS_BAD_WEATHER if (ctx.wet or ctx.snowy) else WEIGHTS
    c.score = 100.0 * sum(weights[k] * v for k, v in c.parts.items())
    c.score -= _PLACE_MISFIT_PENALTY * c.place_misfits
    rejected = ctx.learned.rejected_outfits.get(c.ids(), 0.0)
    if rejected > 0:
        c.was_rejected = True
        c.score -= _REJECTED_OUTFIT_PENALTY * rejected


# ------------------------------------------------------------------ 조합과 선택


def _overlap(a: _Candidate, b: _Candidate, pinned_key: str) -> float:
    """고정 옷을 뺀 나머지가 얼마나 겹치는지 0~1. 신발만 바꾼 조합은 다른 추천으로 덜 쳐 준다."""
    theirs = b.ids()
    total = shared = 0.0
    for g in a.items():
        if str(g.id) == pinned_key:
            continue
        weight = 0.5 if g.category == Category.SHOES else 1.0
        total += weight
        if str(g.id) in theirs:
            shared += weight
    return shared / total if total else 0.0


def _pick_diverse(candidates: list[_Candidate], k: int, pinned_key: str) -> list[_Candidate]:
    pool = sorted(candidates, key=lambda c: c.score, reverse=True)[:300]
    picked: list[_Candidate] = []
    while pool and len(picked) < k:
        best = max(
            pool,
            key=lambda c: c.score - _DIVERSITY_PENALTY * max((_overlap(c, p, pinned_key) for p in picked), default=0.0),
        )
        picked.append(best)
        pool.remove(best)
    return sorted(picked, key=lambda c: c.score, reverse=True)


# ------------------------------------------------------------------ 이유와 근거


def _temp_text(value: float) -> str:
    return f"{round(value)}°C"


_COLOR_PHRASE = {
    "basic": "깔끔하게 어울려요",
    "tone": "톤온톤으로 차분해요",
    "soft": "색감이 자연스럽게 이어져요",
    "contrast": "색 대비로 포인트를 줬어요",
    "same": "같은 색으로 통일했어요",
}


def _reason(c: _Candidate, ctx: _Ctx) -> str:
    temp = _temp_text(ctx.apparent)
    delta = ctx.learned.offset.delta_c
    if delta <= -1.0:
        lead = f"체감 {temp}에 추위를 타는 편이라"
    elif delta >= 1.0:
        lead = f"체감 {temp}에 더위를 타는 편이라"
    else:
        lead = f"체감 {temp}라"

    if c.outer is not None and not _is_pinned(c.outer, ctx):
        first = f"{lead} {josa(c.outer.display_name, '을/를')} 걸쳤고"
    elif c.outer is not None and c.top is not None:
        first = f"{lead} 안에는 {josa(c.top.display_name, '을/를')} 받쳐 입었고"
    elif ctx.effective >= 20.0:
        first = f"{lead} 겉옷 없이 가볍게 입었고"
    elif delta <= -1.0:
        first = f"{lead} 한 단계 따뜻하게 맞췄고"
    elif delta >= 1.0:
        first = f"{lead} 한 단계 가볍게 맞췄고"
    else:
        first = f"{lead} 두께를 맞췄고"

    shoes_free = c.shoes is not None and not _is_pinned(c.shoes, ctx)
    if ctx.snowy and shoes_free and c.shoes.grip:  # type: ignore[union-attr]
        second = f"눈길에 덜 미끄러운 {josa(c.shoes.display_name, '을/를')} 골랐어요"  # type: ignore[union-attr]
    elif ctx.wet and shoes_free and c.shoes.waterproof:  # type: ignore[union-attr]
        second = f"비 소식이 있어 방수되는 {josa(c.shoes.display_name, '을/를')} 골랐어요"  # type: ignore[union-attr]
    elif c.color_partner is not None:
        phrase = _COLOR_PHRASE.get(c.color_relation, f"{ctx.place.value}에 어울리게 맞췄어요")
        partner = josa(c.color_partner.display_name, "을/를")
        second = f"고정한 {ctx.pinned.display_name}에 {partner} 맞춰 {phrase}"
    else:
        second = f"고정한 {josa(ctx.pinned.display_name, '을/를')} 중심으로 잡았어요"
    return f"{first}, {second}."


def _shared_basis(req: RecommendRequest, ctx: _Ctx, n_excluded: int) -> list[Basis]:
    w = req.weather
    weather = f"기온 {_temp_text(w.temp_c)}, 체감 {_temp_text(ctx.apparent)}, {w.sky.value}"
    if ctx.diurnal is not None and ctx.diurnal >= _DIURNAL_C:
        weather += f", 일교차 {round(ctx.diurnal)}°C"
    if w.precip_prob is not None and w.precip_prob >= 0.3:
        weather += f", 강수확률 {round(w.precip_prob * 100)}%"
    basis = [Basis(kind="날씨", text=weather)]

    p = ctx.pinned
    detail = [f"보온 {p.warmth}단계"] if p.warmth is not None else []
    if p.style:
        detail.append(p.style.value)
    if p.colors:
        detail.append("·".join(p.colors))
    pinned_text = f"{p.display_name} 고정" + (f" ({', '.join(detail)})" if detail else "")
    basis.append(Basis(kind="고정 옷", text=pinned_text))

    off = ctx.learned.offset
    if off.n_records == 0:
        feel = "아직 체감 기록이 없어 기본 기준으로 맞췄어요"
    else:
        counts = f"추웠어요 {off.n_cold}·적당했어요 {off.n_ok}·더웠어요 {off.n_hot}"
        if abs(off.delta_c) < 0.5:
            feel = f"체감 기록 {off.n_records}건({counts})을 봤더니 기본 기준과 거의 같아요"
        else:
            direction = "낮춰" if off.delta_c < 0 else "높여"
            feel = f"체감 기록 {off.n_records}건({counts})을 반영해 기준 온도를 {abs(off.delta_c):.1f}°C {direction} 잡았어요"
    basis.append(Basis(kind="체감 기록", text=feel))

    counts_by_reason = ctx.learned.reject_counts
    if counts_by_reason:
        bits = []
        if counts_by_reason.get(RejectReason.TOO_THIN):
            bits.append(f"'너무 얇음' {counts_by_reason[RejectReason.TOO_THIN]}건 → 더 따뜻하게")
        if counts_by_reason.get(RejectReason.COLOR):
            bits.append(f"'색이 안 맞음' {counts_by_reason[RejectReason.COLOR]}건 → 그 색 조합은 뒤로")
        if counts_by_reason.get(RejectReason.PLACE):
            bits.append(f"'장소에 안 맞음' {counts_by_reason[RejectReason.PLACE]}건 → 그 장소에서 해당 옷은 뒤로")
        if counts_by_reason.get(RejectReason.OTHER):
            bits.append(f"직접 입력 {counts_by_reason[RejectReason.OTHER]}건 → 거절한 조합은 뒤로")
        basis.append(Basis(kind="거절 이유", text=", ".join(bits)))

    basis.append(Basis(kind="장소", text=f"'{ctx.place.value}'에 어울리는 스타일을 우선했어요"))
    if n_excluded:
        basis.append(Basis(kind="옷 상태", text=f"세탁·건조·수선 중인 옷 {n_excluded}벌은 빼고 골랐어요"))
    return basis


def _to_recommendation(rank: int, c: _Candidate, ctx: _Ctx, shared: list[Basis]) -> Recommendation:
    slots = ((SLOT_TOP, c.top), (SLOT_BOTTOM, c.bottom), (SLOT_OUTER, c.outer), (SLOT_SHOES, c.shoes))
    items = [
        OutfitItem(
            slot=slot,  # type: ignore[arg-type]
            garment_id=g.id,
            name=g.display_name,
            category=g.category,
            pinned=_is_pinned(g, ctx),
        )
        for slot, g in slots
        if g is not None
    ]
    basis = list(shared)
    if c.diurnal_bonus:
        basis[0] = Basis(kind="날씨", text=basis[0].text + " → 벗기 쉬운 겉옷을 더했어요")
    return Recommendation(
        rank=rank,
        items=items,
        score=round(max(0.0, c.score), 1),
        reason=_reason(c, ctx),
        basis=basis,
        breakdown={k: round(v, 3) for k, v in c.parts.items()},
    )


# ------------------------------------------------------------------ 진입점

_STATUS_TEXT = {Status.LAUNDRY: "세탁 중", Status.DRYING: "건조 중", Status.REPAIR: "수선 중"}


def recommend(req: RecommendRequest) -> RecommendResult:
    """고정한 옷 한 벌을 중심으로 오늘 코디를 추천한다."""
    today = req.today or dt.date.today()
    by_id = {str(g.id): g for g in req.wardrobe}
    pinned = by_id.get(str(req.pinned_id))
    if pinned is None:
        raise ValueError(f"고정한 옷(id={req.pinned_id})이 옷장에 없습니다.")

    learned = learn(req.wear_history, req.rejections, by_id, today)
    weather = req.weather
    apparent = thermal.apparent_temp(weather)
    effective = apparent + learned.offset.delta_c
    diurnal = (
        weather.temp_max_c - weather.temp_min_c
        if weather.temp_max_c is not None and weather.temp_min_c is not None
        else None
    )
    snowy = weather.sky == Sky.SNOW
    wet = weather.sky == Sky.RAIN or (not snowy and (weather.precip_prob or 0.0) >= _WET_PROB)
    ctx = _Ctx(req.place, apparent, effective, wet, snowy, diurnal, learned, pinned)

    excluded = [
        ExcludedGarment(
            garment_id=g.id,
            name=g.display_name,
            status=g.status,
            text=f"{_STATUS_TEXT[g.status]}이라 추천에서 뺐어요",
        )
        for g in req.wardrobe
        if g.status != Status.AVAILABLE
    ]
    context = RecommendContext(
        apparent_temp_c=round(apparent, 1),
        personal_offset_c=round(learned.offset.delta_c, 1),
        effective_temp_c=round(effective, 1),
        wet=wet,
        snowy=snowy,
        diurnal_range_c=round(diurnal, 1) if diurnal is not None else None,
        feedback_counts={
            "추웠어요": learned.offset.n_cold,
            "적당했어요": learned.offset.n_ok,
            "더웠어요": learned.offset.n_hot,
            **{reason.value: n for reason, n in learned.reject_counts.items()},
        },
    )

    warnings: list[str] = []
    if pinned.status != Status.AVAILABLE:
        warnings.append(
            f"고정한 {josa(pinned.display_name, '은/는')} 지금 {_STATUS_TEXT[pinned.status]}이에요. 다른 옷을 고정해 주세요."
        )
        return RecommendResult(recommendations=[], excluded=excluded, context=context, warnings=warnings)

    available = [g for g in req.wardrobe if g.status == Status.AVAILABLE]
    pinned_slot = _SLOT_OF[pinned.category]

    def options(slot: str) -> list[Optional[Garment]]:
        if slot == pinned_slot:
            return [pinned]
        found: list[Optional[Garment]] = [g for g in available if _SLOT_OF[g.category] == slot]
        if slot == SLOT_OUTER:
            if effective >= thermal.NO_OUTER_ABOVE_C:
                # 더운 날에는 겉옷을 붙이지 않는다. 비 오는 날의 방수 겉옷만 예외.
                found = [g for g in found if g is not None and wet and g.waterproof and effective < 28.0]
            return [None, *found]
        if not found:
            warnings.append(f"입을 수 있는 {josa(slot, '이/가')} 없어 빼고 추천했어요.")
            return [None]
        return found

    candidates: list[_Candidate] = []
    for top, bottom, outer, shoes in itertools.product(
        options(SLOT_TOP), options(SLOT_BOTTOM), options(SLOT_OUTER), options(SLOT_SHOES)
    ):
        cand = _Candidate(top, bottom, outer, shoes)
        _score(cand, ctx)
        candidates.append(cand)

    if pinned_slot == SLOT_OUTER and effective >= thermal.NO_OUTER_ABOVE_C:
        warnings.append("오늘은 겉옷을 입기에 더운 날씨예요. 고정한 겉옷은 들고 다니는 걸 추천해요.")
    has_outer = pinned_slot == SLOT_OUTER or any(g.category == Category.OUTER for g in available)
    if thermal.ideal_outer(effective) >= 2.0 and not has_outer:
        warnings.append("입을 수 있는 겉옷이 없어요. 날씨에 비해 얇을 수 있어요.")
    if (wet or snowy) and pinned_slot != SLOT_SHOES:
        shoes = [g for g in available if g.category == Category.SHOES]
        if shoes and snowy and not any(g.grip for g in shoes):
            warnings.append("눈길에 덜 미끄러운 신발이 옷장에 없어요. 걸을 때 조심하세요.")
        elif shoes and wet and not any(g.waterproof for g in shoes):
            warnings.append("방수되는 신발이 옷장에 없어요. 젖어도 괜찮은 신발인지 확인해 주세요.")

    picked = _pick_diverse(candidates, req.top_k, str(pinned.id))
    if picked and picked[0].place_misfits:
        warnings.append(f"'{req.place.value}'에 어울리는 옷이 옷장에 부족해요. 가장 가까운 조합을 골랐어요.")
    shared = _shared_basis(req, ctx, len(excluded))
    recommendations = [_to_recommendation(i + 1, c, ctx, shared) for i, c in enumerate(picked)]
    return RecommendResult(recommendations=recommendations, excluded=excluded, context=context, warnings=warnings)
