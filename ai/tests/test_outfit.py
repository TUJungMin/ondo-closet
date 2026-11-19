"""여러 옷 사진에서 옷을 나누는 규칙. 모델 없이 검출 결과만 흉내 내어 확인한다."""

import numpy as np
from PIL import Image

from ondo_ai.schemas import AnalysisResult, Category, ColorInfo, DetectedGarment, Suggestion, slot_name
from ondo_ai.vision.attributes import suggest_attributes
from ondo_ai.vision.detect import FEET, LOWER, UPPER, Detection, contained, iou, select_garments
from ondo_ai.vision.labels import OTHER_ITEMS, SUBTYPE_PROMPTS, SUBTYPES
from ondo_ai.vision.pipeline import layer_duplicates, save_by_category, strip_overlapping_colors

W, H = 967, 1501


def det(label, score, box):
    """box는 사진 대비 0~1 좌표."""
    return Detection(label, score, (box[0] * W, box[1] * H, box[2] * W, box[3] * H))


# 실제 착용 사진(후드티 + 와이드 팬츠 + 스니커즈 + 가방)에서 검출 모델이 돌려준 결과
REAL_OUTFIT = [
    det("pants", 0.97, (0.34, 0.43, 0.77, 0.97)),
    det("shoe", 0.97, (0.59, 0.93, 0.72, 0.98)),
    det("sleeve", 0.96, (0.33, 0.06, 0.42, 0.36)),
    det("sleeve", 0.96, (0.69, 0.04, 0.88, 0.33)),
    det("shoe", 0.91, (0.34, 0.91, 0.51, 0.96)),
    det("belt", 0.85, (0.39, 0.43, 0.66, 0.47)),
    det("jacket", 0.73, (0.33, 0.00, 0.90, 0.48)),
    det("collar", 0.73, (0.45, 0.00, 0.69, 0.08)),
    det("bag, wallet", 0.71, (0.67, 0.04, 0.90, 0.50)),
    det("pocket", 0.63, (0.65, 0.44, 0.74, 0.59)),
    det("top, t-shirt, sweatshirt", 0.54, (0.46, 0.04, 0.61, 0.30)),
    det("top, t-shirt, sweatshirt", 0.40, (0.36, 0.00, 0.79, 0.45)),
    det("jumpsuit", 0.31, (0.32, 0.00, 0.86, 0.99)),
]


def test_box_helpers():
    a, b = (0, 0, 10, 10), (5, 0, 15, 10)
    assert iou(a, b) == 50 / 150
    assert contained((2, 2, 4, 4), a) == 1.0
    assert contained(a, (2, 2, 4, 4)) == 0.04
    assert iou(a, (20, 20, 30, 30)) == 0.0


def test_real_outfit_is_split_into_upper_lower_and_shoes():
    regions, skipped = select_garments(REAL_OUTFIT, W, H)
    assert [(r.region, r.label) for r in regions] == [
        (UPPER, "jacket"),
        (UPPER, "top, t-shirt, sweatshirt"),  # 후드티 안쪽 상자. 분석 뒤 같은 옷으로 판정되면 빠진다
        (LOWER, "pants"),
        (FEET, "shoe"),
    ]
    assert skipped == ["가방"]


def test_two_shoes_become_one_item():
    regions, _ = select_garments(REAL_OUTFIT, W, H)
    shoes = regions[-1]
    assert shoes.category == Category.SHOES and len(shoes.boxes) == 2
    left, top, right, bottom = shoes.bounds
    assert (round(left / W, 2), round(right / W, 2)) == (0.34, 0.72)
    assert shoes.score == 0.97


def test_parts_low_scores_and_accessories_are_not_garments():
    regions, skipped = select_garments(REAL_OUTFIT, W, H)
    labels = {r.label for r in regions}
    assert not labels & {"sleeve", "collar", "pocket", "belt"}  # 옷의 부분
    assert "jumpsuit" not in labels and "점프수트" not in skipped  # 점수 0.31은 무시


def test_upper_body_lets_the_classifier_choose_top_or_outer():
    regions, _ = select_garments(REAL_OUTFIT, W, H)
    upper, lower, feet = regions[0], regions[2], regions[3]
    assert upper.allowed_categories == {Category.TOP, Category.OUTER}
    assert lower.allowed_categories == {Category.PANTS}
    assert feet.allowed_categories == {Category.SHOES}


def test_tiny_false_positive_is_dropped():
    # 단품 스커트 사진에서 허리띠 부분이 '상의'로 잡힌 실제 사례
    found = [det("skirt", 0.80, (0.00, 0.17, 0.99, 0.94)), det("top, t-shirt, sweatshirt", 0.63, (0.26, 0.00, 0.74, 0.05))]
    regions, _ = select_garments(found, 1280, 1268)
    assert [r.label for r in regions] == ["skirt"]


def test_same_garment_detected_twice_keeps_the_better_box():
    found = [det("jacket", 0.80, (0.30, 0.05, 0.90, 0.50)), det("coat", 0.60, (0.31, 0.04, 0.89, 0.52))]
    regions, _ = select_garments(found, W, H)
    assert [r.label for r in regions] == ["jacket"]


def test_partial_box_of_same_category_is_dropped():
    # 단품 바지 사진에서 한쪽 다리만 다시 잡힌 실제 사례 (점수를 올려서 재현)
    found = [det("pants", 0.79, (0.05, 0.04, 0.93, 0.96)), det("pants", 0.60, (0.42, 0.37, 0.60, 1.00))]
    regions, _ = select_garments(found, W, H)
    assert len(regions) == 1 and regions[0].score == 0.79


def test_dress_is_reported_as_skipped():
    regions, skipped = select_garments([det("dress", 0.90, (0.2, 0.1, 0.8, 0.9))], W, H)
    assert regions == [] and skipped == ["원피스"]


def test_nothing_found():
    assert select_garments([det("sleeve", 0.9, (0.1, 0.1, 0.3, 0.6))], W, H) == ([], [])


# ---------------------------------------------------------------- 분석 뒤 정리


def garment(box, category, colors):
    return DetectedGarment(
        box=list(box),
        detector_label="x",
        detector_score=0.9,
        analysis=AnalysisResult(
            category=Suggestion(value=category),
            colors=[ColorInfo(name=name, hex="#000000", ratio=0.5) for name in colors],
        ),
    )


def test_inner_box_with_same_category_is_the_same_garment():
    hoodie = garment((0.33, 0.00, 0.90, 0.48), "상의", ["갈색"])
    chest = garment((0.46, 0.04, 0.61, 0.30), "상의", ["갈색"])
    assert layer_duplicates([hoodie, chest], [UPPER, UPPER]) == {1}


def test_inner_box_with_same_color_is_the_same_garment():
    outer = garment((0.30, 0.05, 0.90, 0.60), "겉옷", ["갈색"])
    inner = garment((0.45, 0.10, 0.75, 0.50), "상의", ["갈색"])
    assert layer_duplicates([outer, inner], [UPPER, UPPER]) == {1}


def test_layered_garments_of_different_category_and_color_are_both_kept():
    coat = garment((0.30, 0.05, 0.90, 0.80), "겉옷", ["베이지"])
    knit = garment((0.45, 0.10, 0.75, 0.50), "상의", ["버건디"])
    assert layer_duplicates([coat, knit], [UPPER, UPPER]) == set()


def test_shoes_under_the_trouser_box_are_never_treated_as_duplicates():
    pants = garment((0.34, 0.43, 0.77, 0.97), "바지", ["검정"])
    shoes = garment((0.34, 0.91, 0.72, 0.98), "신발", ["검정", "아이보리"])
    assert layer_duplicates([pants, shoes], [LOWER, FEET]) == set()


def test_trouser_color_is_removed_from_shoes_under_the_hem():
    pants = garment((0.34, 0.43, 0.77, 0.97), "바지", ["검정"])
    shoes = garment((0.34, 0.91, 0.72, 0.98), "신발", ["검정", "아이보리"])
    strip_overlapping_colors([pants, shoes], [LOWER, FEET])
    assert [c.name for c in shoes.analysis.colors] == ["아이보리"]
    assert [c.name for c in pants.analysis.colors] == ["검정"]


def test_single_color_is_kept_even_if_it_matches_the_overlapping_garment():
    pants = garment((0.34, 0.43, 0.77, 0.97), "바지", ["검정"])
    shoes = garment((0.34, 0.91, 0.72, 0.98), "신발", ["검정"])
    strip_overlapping_colors([pants, shoes], [LOWER, FEET])
    assert [c.name for c in shoes.analysis.colors] == ["검정"]


def test_slight_overlap_does_not_change_colors():
    # 줄무늬 상의의 밑단이 흰 바지 상자에 조금 걸친 경우: 상의의 흰색은 그대로 둔다
    top = garment((0.30, 0.05, 0.80, 0.48), "상의", ["남색", "흰색"])
    pants = garment((0.34, 0.43, 0.77, 0.97), "바지", ["흰색"])
    strip_overlapping_colors([top, pants], [UPPER, LOWER])
    assert [c.name for c in top.analysis.colors] == ["남색", "흰색"]


# ---------------------------------------------------------------- 종류별 폴더에 저장


def test_slot_names():
    assert [slot_name(c) for c in ("상의", "바지", "스커트", "겉옷", "신발")] == ["상의", "하의", "하의", "겉옷", "신발"]
    assert slot_name(Category.SKIRT) == "하의"
    assert slot_name(None) == "미분류" and slot_name("원피스") == "미분류"


def test_cutouts_are_saved_into_a_folder_per_slot(tmp_path):
    picture = Image.new("RGBA", (20, 30), (200, 30, 30, 255))
    saved = {}
    for index, category in enumerate(("상의", "바지", "스커트", "겉옷", "신발", None), start=1):
        analysis = AnalysisResult(category=Suggestion(value=category))
        path = save_by_category(picture, analysis, tmp_path / "결과", f"ootd_{index}")
        assert analysis.cutout_path == str(path) and path.is_file()
        saved[category] = path.relative_to(tmp_path / "결과").as_posix()
    assert saved == {
        "상의": "상의/ootd_1.png",
        "바지": "하의/ootd_2.png",
        "스커트": "하의/ootd_3.png",
        "겉옷": "겉옷/ootd_4.png",
        "신발": "신발/ootd_5.png",
        None: "미분류/ootd_6.png",
    }
    assert Image.open(tmp_path / "결과" / "상의" / "ootd_1.png").mode == "RGBA"


def test_nothing_is_saved_when_there_is_no_cutout(tmp_path):
    analysis = AnalysisResult(category=Suggestion(value="상의"))
    assert save_by_category(None, analysis, tmp_path, "x") is None
    assert analysis.cutout_path is None and list(tmp_path.iterdir()) == []


# ---------------------------------------------------------------- 종류를 좁혀서 분류


class FakeClassifier:
    """세부 종류 문구에 대해 정해 둔 확률을 돌려주는 가짜 분류기."""

    model_id = "fake"

    def __init__(self, favorites):
        self.favorites = favorites

    def probabilities(self, embedding, prompts):
        if tuple(prompts) != SUBTYPE_PROMPTS:
            return np.full(len(prompts), 1 / len(prompts))
        names = [s.name for s in SUBTYPES] + [name for name, _ in OTHER_ITEMS]
        probs = np.array([self.favorites.get(name, 0.0) for name in names])
        return probs / probs.sum()


def test_restricting_to_shoes_fixes_a_crop_dominated_by_trouser_hem():
    # 바짓단이 같이 찍힌 신발 영역: 그냥 분류하면 바지가 이긴다
    classifier = FakeClassifier({"코듀로이 팬츠": 0.60, "스니커즈": 0.30, "러닝화": 0.10})
    free = suggest_attributes(classifier, None)
    assert free.category.value == "바지"
    restricted = suggest_attributes(classifier, None, allowed={Category.SHOES})
    assert restricted.category.value == "신발"
    assert restricted.subtype.value == "스니커즈"
    assert [c.label for c in restricted.category.candidates] == ["신발"]
    assert restricted.grip is True


def test_upper_body_chooses_between_top_and_outer_only():
    classifier = FakeClassifier({"후드티": 0.50, "후드 집업": 0.20, "가방": 0.30})
    result = suggest_attributes(classifier, None, allowed={Category.TOP, Category.OUTER})
    assert result.category.value == "상의" and result.subtype.value == "후드티"
    assert result.warnings == []


def test_without_restriction_low_confidence_still_leaves_category_empty():
    classifier = FakeClassifier({"후드티": 0.45, "코듀로이 팬츠": 0.45, "스니커즈": 0.10})
    result = suggest_attributes(classifier, None)
    assert result.category.value is None and result.warnings
