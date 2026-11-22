"""착용 사진 평가(scripts/evaluate.py)의 채점 규칙 확인. 모델을 올리지 않는다."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from evaluate import parse_expected, score_outfit  # noqa: E402

UPPER, LOWER, FEET = "상체", "하체", "발"


def test_parse_expected_splits_and_validates():
    assert parse_expected("상의;바지;신발") == ["상의", "바지", "신발"]
    assert parse_expected(" 상의 ; 겉옷;스커트 ; 신발 ") == ["상의", "겉옷", "스커트", "신발"]
    with pytest.raises(ValueError):
        parse_expected("상의;원피스")
    with pytest.raises(ValueError):
        parse_expected("")


def test_everything_found_with_right_categories():
    score = score_outfit(["상의", "바지", "신발"], [(UPPER, "상의"), (LOWER, "바지"), (FEET, "신발")])
    assert (score.expected, score.found, score.false_finds, score.category_right) == (3, 3, 0, 3)
    assert score.missed == []


def test_missed_garment_lowers_recall():
    # 겉옷 안의 상의를 놓친 경우
    score = score_outfit(["상의", "겉옷", "바지", "신발"], [(UPPER, "겉옷"), (LOWER, "바지"), (FEET, "신발")])
    assert (score.expected, score.found, score.false_finds, score.category_right) == (4, 3, 0, 3)
    assert score.missed == ["상의"]


def test_extra_detection_counts_as_false_find():
    score = score_outfit(["상의", "바지"], [(UPPER, "상의"), (LOWER, "바지"), (FEET, "신발")])
    assert (score.found, score.false_finds, score.category_right) == (2, 1, 2)
    assert score.missed == []


def test_found_but_wrong_category_is_not_a_miss():
    # 긴 스커트를 바지로 본 경우: 찾기는 했지만 종류가 틀렸다
    score = score_outfit(["상의", "스커트", "신발"], [(UPPER, "상의"), (LOWER, "바지"), (FEET, "신발")])
    assert (score.found, score.false_finds, score.category_right) == (3, 0, 2)
    assert score.missed == []


def test_blank_category_counts_as_found_but_not_right():
    score = score_outfit(["상의", "바지"], [(UPPER, None), (LOWER, "바지")])
    assert (score.found, score.false_finds, score.category_right) == (2, 0, 1)


def test_nothing_found():
    score = score_outfit(["상의", "바지", "신발"], [])
    assert (score.found, score.false_finds, score.category_right) == (0, 0, 0)
    assert sorted(score.missed) == ["바지", "상의", "신발"]


def test_ambiguous_miss_reports_part_only():
    # 상체 두 벌 중 하나만 찾았고 그 종류도 비어 있으면, 어느 쪽을 놓쳤는지 알 수 없다
    score = score_outfit(["상의", "겉옷"], [(UPPER, None)])
    assert (score.found, score.category_right) == (1, 0)
    assert score.missed == ["상체 1벌"]


def test_same_category_twice():
    score = score_outfit(["상의", "상의", "바지"], [(UPPER, "상의"), (LOWER, "바지")])
    assert (score.expected, score.found, score.category_right) == (3, 2, 2)
    assert score.missed == ["상의"]
