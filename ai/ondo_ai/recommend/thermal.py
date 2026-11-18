"""기온 → 필요한 보온 정도, 그리고 체감 기록으로 구하는 개인 보정.

옷의 보온성은 1(한여름용)~5(한겨울용) 단계다. 코디 전체 보온 지수는

    상의 + 1.3 × 겉옷 + 0.5 × 하의

로 본다. (겉옷이 체감에 가장 크게 작용하고, 하의는 덜 작용한다는 가정)
아래 표는 '이 기온이면 슬롯별로 이 정도 두께'라는 기준선이며, 평가·시연 중 어색하면 이 표를 고친다.
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass
from typing import Optional, Sequence

from ..schemas import Category, Feeling, Garment, RejectReason, Rejection, WearRecord, Weather

OUTER_WEIGHT = 1.3
BOTTOM_WEIGHT = 0.5
DEFAULT_WARMTH = 3  # 보온성을 모를 때

#            기온   -8    0    5    9    12   16   19   22   26   30
_ANCHOR_T = (-8.0, 0.0, 5.0, 9.0, 12.0, 16.0, 19.0, 22.0, 26.0, 30.0)
_TOP = (5.0, 4.0, 4.0, 3.5, 3.0, 3.0, 2.5, 2.0, 1.0, 1.0)
_BOTTOM = (4.5, 4.0, 3.5, 3.0, 3.0, 3.0, 3.0, 2.5, 2.0, 1.0)
_OUTER = (5.0, 5.0, 4.0, 3.5, 3.0, 2.0, 1.0, 0.0, 0.0, 0.0)
_SHOES = (4.5, 4.0, 3.5, 3.0, 3.0, 3.0, 3.0, 2.5, 2.0, 1.5)
_TOTAL = tuple(t + OUTER_WEIGHT * o + BOTTOM_WEIGHT * b for t, o, b in zip(_TOP, _OUTER, _BOTTOM))

NO_OUTER_ABOVE_C = 24.0  # 이보다 따뜻하면 겉옷을 붙이지 않는다

_COLD_SHIFT_C = 3.0  # '추웠어요/더웠어요' 한 번이 뜻하는 온도 차이
_THIN_SHIFT_C = 2.0  # '너무 얇음' 거절 한 번
_OK_WEIGHT = 0.6
_THIN_WEIGHT = 0.7
_PRIOR_WEIGHT = 1.5  # 기록이 적을 때 보정이 튀지 않게 0 쪽으로 당기는 힘
_HALF_LIFE_DAYS = 21.0
_MAX_OFFSET_C = 6.0


def _interp(x: float, xs: Sequence[float], ys: Sequence[float]) -> float:
    """xs 오름차순 선형 보간. 범위를 벗어나면 끝값."""
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(1, len(xs)):
        if x <= xs[i]:
            ratio = (x - xs[i - 1]) / (xs[i] - xs[i - 1])
            return ys[i - 1] + ratio * (ys[i] - ys[i - 1])
    return ys[-1]


def ideal_top(temp_c: float) -> float:
    return _interp(temp_c, _ANCHOR_T, _TOP)


def ideal_bottom(temp_c: float) -> float:
    return _interp(temp_c, _ANCHOR_T, _BOTTOM)


def ideal_outer(temp_c: float) -> float:
    return _interp(temp_c, _ANCHOR_T, _OUTER)


def ideal_shoes(temp_c: float) -> float:
    return _interp(temp_c, _ANCHOR_T, _SHOES)


def target_warmth(temp_c: float) -> float:
    """이 기온에서 알맞은 코디 전체 보온 지수."""
    return _interp(temp_c, _ANCHOR_T, _TOTAL)


def equivalent_temp(warmth_index: float) -> float:
    """보온 지수가 딱 맞는 기온. target_warmth의 역함수."""
    return _interp(warmth_index, _TOTAL[::-1], _ANCHOR_T[::-1])


def warmth_of(garment: Optional[Garment]) -> float:
    if garment is None:
        return 0.0
    return float(garment.warmth if garment.warmth is not None else DEFAULT_WARMTH)


def outfit_warmth(top: Optional[Garment], bottom: Optional[Garment], outer: Optional[Garment]) -> float:
    t = warmth_of(top) if top else DEFAULT_WARMTH
    b = warmth_of(bottom) if bottom else DEFAULT_WARMTH
    return t + OUTER_WEIGHT * warmth_of(outer) + BOTTOM_WEIGHT * b


def apparent_temp(weather: Weather) -> float:
    """체감 온도. 값이 오면 그대로 쓰고, 없으면 10°C 이하에서 바람으로 추정한다."""
    if weather.feels_like_c is not None:
        return weather.feels_like_c
    t = weather.temp_c
    wind_kmh = (weather.wind_ms or 0.0) * 3.6
    if t <= 10.0 and wind_kmh >= 4.8:
        v = wind_kmh**0.16
        return min(t, 13.12 + 0.6215 * t - 11.37 * v + 0.3965 * t * v)
    return t


def recency_weight(date: Optional[dt.date], today: dt.date, half_life_days: float = _HALF_LIFE_DAYS) -> float:
    if date is None:
        return 1.0
    age = max(0, (today - date).days)
    return 0.5 ** (age / half_life_days)


@dataclass
class OffsetEstimate:
    """개인 체감 보정. delta_c가 음수면 추위를 타는 편(같은 날씨를 더 춥게 느낌)."""

    delta_c: float = 0.0
    n_cold: int = 0
    n_ok: int = 0
    n_hot: int = 0
    n_thin: int = 0

    @property
    def n_records(self) -> int:
        return self.n_cold + self.n_ok + self.n_hot


def _worn_warmth(item_ids: Sequence, by_id: dict[str, Garment]) -> Optional[float]:
    top = bottom = outer = None
    for item_id in item_ids:
        g = by_id.get(str(item_id))
        if g is None:
            continue
        if g.category == Category.TOP:
            top = g
        elif g.category in (Category.PANTS, Category.SKIRT):
            bottom = g
        elif g.category == Category.OUTER:
            outer = g
    if top is None and bottom is None:
        return None
    return outfit_warmth(top, bottom, outer)


def estimate_offset(
    wear_history: Sequence[WearRecord],
    rejections: Sequence[Rejection],
    by_id: dict[str, Garment],
    today: dt.date,
) -> OffsetEstimate:
    """착용 기록과 '너무 얇음' 거절로 개인 보정 온도를 추정한다.

    한 기록의 뜻: 기온 T에 보온 지수 W로 입었더니 '적당했다'면, 이 사람에게 T는
    기준선에서 W가 딱 맞는 기온 T_eq(W)처럼 느껴진 것이다 → 보정 표본 = T_eq(W) − T.
    '추웠다'면 그보다 더 춥게, '더웠다'면 더 덥게 느낀 것으로 본다.
    최근 기록일수록 크게 반영하고, 기록이 적을 때는 0 쪽으로 당긴다.
    """
    est = OffsetEstimate()
    weighted_sum = 0.0
    weight_total = 0.0

    def add(sample: float, weight: float) -> None:
        nonlocal weighted_sum, weight_total
        sample = max(-8.0, min(8.0, sample))
        weighted_sum += weight * sample
        weight_total += weight

    for rec in wear_history:
        if rec.feeling is None:
            continue
        worn = _worn_warmth(rec.item_ids, by_id)
        residual = (equivalent_temp(worn) - rec.temp_c) if worn is not None else 0.0
        w = recency_weight(rec.date, today)
        if rec.feeling == Feeling.COLD:
            est.n_cold += 1
            add(residual - _COLD_SHIFT_C, w)
        elif rec.feeling == Feeling.HOT:
            est.n_hot += 1
            add(residual + _COLD_SHIFT_C, w)
        else:
            est.n_ok += 1
            add(residual, w * _OK_WEIGHT)

    for rej in rejections:
        if rej.reason != RejectReason.TOO_THIN:
            continue
        est.n_thin += 1
        worn = _worn_warmth(rej.item_ids, by_id)
        residual = (equivalent_temp(worn) - rej.temp_c) if (worn is not None and rej.temp_c is not None) else 0.0
        add(residual - _THIN_SHIFT_C, recency_weight(rej.date, today) * _THIN_WEIGHT)

    if weight_total > 0:
        delta = weighted_sum / (weight_total + _PRIOR_WEIGHT)
        est.delta_c = max(-_MAX_OFFSET_C, min(_MAX_OFFSET_C, delta))
    return est


def gaussian_fit(value: float, ideal: float, tolerance: float) -> float:
    """ideal에서 멀어질수록 1 → 0으로 떨어지는 점수."""
    return math.exp(-(((value - ideal) / tolerance) ** 2))
