import datetime as dt

import pytest

from ondo_ai import (
    Category,
    Feeling,
    Garment,
    Place,
    RecommendRequest,
    Rejection,
    RejectReason,
    Sky,
    Status,
    WearRecord,
    Weather,
    recommend,
)
from ondo_ai.recommend import thermal
from ondo_ai.sample import autumn_wardrobe

TODAY = dt.date(2026, 11, 18)
BEIGE_KNIT, JEANS, TRENCH, SNEAKERS = 2, 9, 17, 25


def ask(pinned_id=BEIGE_KNIT, temp=14.0, wardrobe=None, **kwargs):
    weather_keys = ("sky", "temp_min_c", "temp_max_c", "feels_like_c", "wind_ms", "precip_prob")
    weather = Weather(temp_c=temp, **{k: kwargs.pop(k) for k in weather_keys if k in kwargs})
    return recommend(
        RecommendRequest(
            wardrobe=wardrobe or autumn_wardrobe(), pinned_id=pinned_id, weather=weather, today=TODAY, **kwargs
        )
    )


def ids(rec):
    return {item.garment_id for item in rec.items}


def by_slot(rec):
    return {item.slot: item for item in rec.items}


def wardrobe_by_id():
    return {g.id: g for g in autumn_wardrobe()}


# ---------------------------------------------------------------- 한 벌 고정


def test_pinned_garment_is_in_every_recommendation():
    result = ask(top_k=5)
    assert len(result.recommendations) == 5
    for rec in result.recommendations:
        pinned = [item for item in rec.items if item.pinned]
        assert [item.garment_id for item in pinned] == [BEIGE_KNIT]
        assert by_slot(rec)["상의"].garment_id == BEIGE_KNIT


@pytest.mark.parametrize("pinned_id, slot", [(JEANS, "하의"), (15, "하의"), (TRENCH, "겉옷"), (SNEAKERS, "신발")])
def test_any_category_can_be_pinned(pinned_id, slot):
    for rec in ask(pinned_id=pinned_id).recommendations:
        assert by_slot(rec)[slot].garment_id == pinned_id
        assert by_slot(rec)[slot].pinned


def test_recommendations_are_ranked_and_distinct():
    recs = ask(top_k=5).recommendations
    assert [r.rank for r in recs] == [1, 2, 3, 4, 5]
    assert [r.score for r in recs] == sorted((r.score for r in recs), reverse=True)
    assert len({frozenset(ids(r)) for r in recs}) == 5


def test_unknown_pinned_id_raises():
    with pytest.raises(ValueError):
        ask(pinned_id=999)


# ---------------------------------------------------------------- 옷 상태 제외


def test_unavailable_garments_are_never_recommended():
    result = ask(top_k=10)
    unavailable = {g.id for g in autumn_wardrobe() if g.status != Status.AVAILABLE}
    assert unavailable == {4, 8, 16}
    assert {e.garment_id for e in result.excluded} == unavailable
    for rec in result.recommendations:
        assert not ids(rec) & unavailable
        assert any(b.kind == "옷 상태" for b in rec.basis)


def test_pinning_a_garment_in_the_wash_gives_no_outfit_and_says_why():
    result = ask(pinned_id=8)
    assert result.recommendations == []
    assert "세탁 중" in result.warnings[0]


def test_status_change_removes_garment_from_results():
    wardrobe = autumn_wardrobe()
    before = ask(wardrobe=wardrobe)
    top_pick = next(i for i in before.recommendations[0].items if not i.pinned)
    for g in wardrobe:
        if g.id == top_pick.garment_id:
            g.status = Status.LAUNDRY
    after = ask(wardrobe=wardrobe, top_k=10)
    assert all(top_pick.garment_id not in ids(rec) for rec in after.recommendations)


# ---------------------------------------------------------------- 날씨


def test_colder_weather_means_warmer_outfit():
    garments = wardrobe_by_id()

    def warmth(rec):
        slots = by_slot(rec)
        get = lambda s: garments[slots[s].garment_id] if s in slots else None  # noqa: E731
        return thermal.outfit_warmth(get("상의"), get("하의"), get("겉옷"))

    hot = warmth(ask(pinned_id=JEANS, temp=27).recommendations[0])
    mild = warmth(ask(pinned_id=JEANS, temp=17).recommendations[0])
    cold = warmth(ask(pinned_id=JEANS, temp=3).recommendations[0])
    assert hot < mild < cold


def test_no_outerwear_on_a_hot_day_and_outerwear_on_a_cold_day():
    for rec in ask(pinned_id=JEANS, temp=28, top_k=5).recommendations:
        assert "겉옷" not in by_slot(rec)
    for rec in ask(pinned_id=JEANS, temp=4, top_k=5).recommendations:
        assert "겉옷" in by_slot(rec)


def test_rain_picks_waterproof_shoes():
    garments = wardrobe_by_id()
    dry = ask(temp=14).recommendations[0]
    wet = ask(temp=14, sky=Sky.RAIN).recommendations[0]
    assert garments[by_slot(wet)["신발"].garment_id].waterproof
    assert "방수" in wet.reason
    assert "방수" not in dry.reason


def test_rain_beats_dress_code_for_shoes():
    garments = wardrobe_by_id()
    office = ask(pinned_id=10, temp=9, sky=Sky.RAIN, place=Place.OFFICE).recommendations[0]
    assert garments[by_slot(office)["신발"].garment_id].waterproof


def test_high_rain_probability_counts_as_wet():
    assert ask(precip_prob=0.7).context.wet
    assert not ask(precip_prob=0.3).context.wet


def test_rain_boots_stay_home_on_a_dry_day():
    rain_boots = 29
    for pinned_id in (BEIGE_KNIT, JEANS, TRENCH):
        for rec in ask(pinned_id=pinned_id, temp=14, top_k=3).recommendations:
            assert rain_boots not in ids(rec)


def test_rain_without_waterproof_shoes_warns():
    wardrobe = [g for g in autumn_wardrobe() if not (g.category == Category.SHOES and g.waterproof)]
    result = ask(wardrobe=wardrobe, sky=Sky.RAIN)
    assert any("방수되는 신발이 옷장에 없어요" in w for w in result.warnings)
    assert not any("방수" in w for w in ask(sky=Sky.RAIN).warnings)


def test_snow_picks_shoes_with_grip():
    garments = wardrobe_by_id()
    snowy = ask(temp=-1, sky=Sky.SNOW).recommendations[0]
    assert garments[by_slot(snowy)["신발"].garment_id].grip


def test_wind_lowers_apparent_temperature():
    calm = ask(temp=5)
    windy = ask(temp=5, wind_ms=8)
    assert windy.context.apparent_temp_c < calm.context.apparent_temp_c == 5


def test_large_daily_range_is_reported():
    result = ask(temp=18, temp_min_c=8, temp_max_c=20)
    assert result.context.diurnal_range_c == 12
    assert "일교차 12°C" in result.recommendations[0].basis[0].text


# ---------------------------------------------------------------- 장소


def test_place_changes_the_style_of_the_outfit():
    garments = wardrobe_by_id()

    def styles(place):
        rec = ask(pinned_id=1, temp=16, place=place).recommendations[0]
        return [garments[i.garment_id].style.value for i in rec.items if not i.pinned]

    assert styles(Place.FORMAL).count("포멀") > styles(Place.SPORT).count("포멀")
    assert styles(Place.SPORT).count("스포티") > styles(Place.FORMAL).count("스포티")


# ---------------------------------------------------------------- 체감 기록


def _baseline_temp(item_ids=(1, 9, 19)):
    """이 옷차림이 기준선상 딱 맞는 기온. 추천받은 대로 입은 날을 흉내 낸다."""
    garments = wardrobe_by_id()
    top, bottom, outer = (garments[i] for i in item_ids)
    return thermal.equivalent_temp(thermal.outfit_warmth(top, bottom, outer))


def _wear(feeling, days_ago, item_ids=(1, 9, 19), temp=None):
    temp = _baseline_temp(item_ids) if temp is None else temp
    return WearRecord(date=TODAY - dt.timedelta(days=days_ago), item_ids=list(item_ids), temp_c=temp, feeling=feeling)


def test_no_history_means_no_personal_offset():
    result = ask()
    assert result.context.personal_offset_c == 0
    basis = {b.kind: b.text for b in result.recommendations[0].basis}
    assert "아직 체감 기록이 없어" in basis["체감 기록"]


def test_cold_records_shift_toward_warmer_outfits():
    garments = wardrobe_by_id()
    history = [_wear(Feeling.COLD, d) for d in (1, 3, 6)]
    base = ask(pinned_id=JEANS, temp=16)
    adjusted = ask(pinned_id=JEANS, temp=16, wear_history=history)
    assert adjusted.context.personal_offset_c < -1
    assert adjusted.context.effective_temp_c < base.context.effective_temp_c

    def warmth(result):
        slots = by_slot(result.recommendations[0])
        get = lambda s: garments[slots[s].garment_id] if s in slots else None  # noqa: E731
        return thermal.outfit_warmth(get("상의"), get("하의"), get("겉옷"))

    assert warmth(adjusted) > warmth(base)
    assert "추위를 타는 편" in adjusted.recommendations[0].reason
    basis = {b.kind: b.text for b in adjusted.recommendations[0].basis}
    assert "추웠어요 3" in basis["체감 기록"]


def test_hot_records_shift_the_other_way():
    history = [_wear(Feeling.HOT, d) for d in (1, 3, 6)]
    result = ask(pinned_id=JEANS, temp=16, wear_history=history)
    assert result.context.personal_offset_c > 1
    assert "더위를 타는 편" in result.recommendations[0].reason


def test_just_right_records_keep_the_baseline():
    # 기준선대로 입고 적당했다면 보정은 거의 0
    history = [_wear(Feeling.OK, d) for d in (1, 2, 3)]
    assert abs(ask(wear_history=history).context.personal_offset_c) < 0.3


def test_feeling_cold_in_a_too_light_outfit_is_weak_evidence():
    # 기준보다 얇게 입고 추웠던 건 누구나 추울 상황이라, 맞게 입고 추웠던 것보다 덜 반영한다.
    dressed_right = ask(wear_history=[_wear(Feeling.COLD, 1)]).context.personal_offset_c
    underdressed = ask(wear_history=[_wear(Feeling.COLD, 1, temp=_baseline_temp() - 2)]).context.personal_offset_c
    assert dressed_right < underdressed <= 0


def test_old_records_count_less_than_recent_ones():
    recent = ask(wear_history=[_wear(Feeling.COLD, 1)]).context.personal_offset_c
    old = ask(wear_history=[_wear(Feeling.COLD, 90)]).context.personal_offset_c
    assert recent < old < 0


def test_one_record_does_not_swing_the_offset():
    assert -2.5 < ask(wear_history=[_wear(Feeling.COLD, 0)]).context.personal_offset_c < 0


# ---------------------------------------------------------------- 거절 이유


def _reject(rec, reason, **kwargs):
    return Rejection(
        date=TODAY, item_ids=[i.garment_id for i in rec.items], pinned_id=BEIGE_KNIT, reason=reason, **kwargs
    )


@pytest.mark.parametrize("reason", list(RejectReason))
def test_rejected_outfit_drops_from_first_place(reason):
    first = ask().recommendations[0]
    again = ask(rejections=[_reject(first, reason, temp_c=14.0, place=Place.DAILY)])
    assert ids(again.recommendations[0]) != ids(first)
    assert any(b.kind == "거절 이유" for b in again.recommendations[0].basis)


def test_too_thin_rejection_makes_next_outfits_warmer():
    first = ask(temp=14)
    again = ask(temp=14, rejections=[_reject(first.recommendations[0], RejectReason.TOO_THIN, temp_c=14.0)])
    assert again.context.personal_offset_c < 0
    assert again.context.feedback_counts["너무 얇음"] == 1


def test_color_rejection_pushes_that_color_pair_down():
    wardrobe = [
        Garment(id="top", name="버건디 니트", category=Category.TOP, colors=["버건디"], warmth=3),
        Garment(id="green", name="초록 바지", category=Category.PANTS, colors=["초록"], warmth=3),
        Garment(id="khaki", name="카키 바지", category=Category.PANTS, colors=["카키"], warmth=3),
        Garment(id="green2", name="초록 치마", category=Category.SKIRT, colors=["초록"], warmth=3),
    ]

    def order(rejections=()):
        result = ask(pinned_id="top", temp=20, wardrobe=wardrobe, rejections=list(rejections), top_k=3)
        return [by_slot(r)["하의"].garment_id for r in result.recommendations]

    assert order()[0] == "khaki"
    rejection = Rejection(date=TODAY, item_ids=["top", "khaki"], pinned_id="top", reason=RejectReason.COLOR)
    after = order([rejection])
    assert after[-1] == "khaki"  # 거절한 색 조합이 맨 뒤로


def test_place_rejection_only_applies_to_that_place():
    first = ask(place=Place.OFFICE).recommendations[0]
    rejection = _reject(first, RejectReason.PLACE, place=Place.OFFICE)
    rejected_items = ids(first) - {BEIGE_KNIT}

    office = ask(place=Place.OFFICE, rejections=[rejection]).recommendations[0]
    assert ids(office) != ids(first)
    assert len(ids(office) & rejected_items) < len(rejected_items)


# ---------------------------------------------------------------- 근거와 예외 상황


def test_every_recommendation_explains_itself():
    for rec in ask(top_k=5).recommendations:
        assert rec.reason.endswith(".") and "체감 14°C" in rec.reason and "고정한 베이지 니트" in rec.reason
        kinds = [b.kind for b in rec.basis]
        assert {"날씨", "고정 옷", "체감 기록"} <= set(kinds)
        assert set(rec.breakdown) == {"보온", "색", "스타일·장소", "날씨 대비", "선호"}
        assert all(0 <= v <= 1 for v in rec.breakdown.values())
        assert 0 <= rec.score <= 100


def test_missing_slot_is_skipped_with_a_warning():
    wardrobe = [g for g in autumn_wardrobe() if g.category != Category.SHOES]
    result = ask(wardrobe=wardrobe)
    assert any("신발" in w for w in result.warnings)
    assert all("신발" not in by_slot(rec) for rec in result.recommendations)


def test_wardrobe_with_only_the_pinned_garment_still_answers():
    wardrobe = [Garment(id=1, name="흰 티셔츠", category=Category.TOP, colors=["흰색"], warmth=1)]
    result = ask(pinned_id=1, wardrobe=wardrobe, temp=25)
    assert len(result.recommendations) == 1
    assert [i.garment_id for i in result.recommendations[0].items] == [1]


def test_garment_without_ai_attributes_is_still_usable():
    wardrobe = autumn_wardrobe() + [Garment(id=99, category=Category.TOP)]
    result = ask(pinned_id=99, wardrobe=wardrobe)
    assert result.recommendations and "고정한 상의" in result.recommendations[0].reason


def test_integer_and_string_ids_match():
    assert ask(pinned_id="2").recommendations[0].items[0].garment_id == 2


def test_request_round_trips_through_json():
    request = RecommendRequest(
        wardrobe=autumn_wardrobe(),
        pinned_id=BEIGE_KNIT,
        weather=Weather(temp_c=12, sky=Sky.CLOUDY),
        place=Place.DATE,
        wear_history=[_wear(Feeling.OK, 2)],
        today=TODAY,
    )
    restored = RecommendRequest.model_validate_json(request.model_dump_json())
    assert recommend(restored).model_dump() == recommend(request).model_dump()
