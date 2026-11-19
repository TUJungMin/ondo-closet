import numpy as np
import pytest
from PIL import Image, ImageDraw

from ondo_ai.palette import PALETTE, pair_harmony
from ondo_ai.text import josa
from ondo_ai.vision.color import ciede2000, extract_colors, hex_to_lab, lab_to_hex, name_color


@pytest.mark.parametrize(
    "word, pair, expected",
    [
        ("니트", "을/를", "니트를"),
        ("청바지", "을/를", "청바지를"),
        ("슬랙스", "을/를", "슬랙스를"),
        ("트렌치코트", "을/를", "트렌치코트를"),
        ("패딩", "을/를", "패딩을"),
        ("신발", "이/가", "신발이"),
        ("상의", "이/가", "상의가"),
        ("레인부츠", "으로/로", "레인부츠로"),
        ("운동화", "으로/로", "운동화로"),
        ("패딩", "으로/로", "패딩으로"),
        ("스웨터 2", "을/를", "스웨터 2를"),
    ],
)
def test_josa(word, pair, expected):
    assert josa(word, pair) == expected


def test_ciede2000_matches_published_reference_pairs():
    # Sharma, Wu, Dalal (2005) 검증 표의 앞 세 쌍
    reference = np.array([50.0, 0.0, -82.7485])
    samples = np.array([[50.0, 2.6772, -79.7751], [50.0, 3.1571, -77.2803], [50.0, 2.8361, -74.0200]])
    assert ciede2000(samples, reference) == pytest.approx([2.0425, 2.8615, 3.4412], abs=1e-4)


def test_lab_round_trip():
    for value in ("#c19a6b", "#1f2a44", "#ffffff", "#000000", "#d32f2f"):
        assert lab_to_hex(hex_to_lab(value)) == value


def test_every_palette_swatch_gets_its_own_name():
    for color in PALETTE:
        for swatch in color.swatches:
            assert name_color(hex_to_lab(swatch)) == color.name, swatch


@pytest.mark.parametrize(
    "value, expected",
    [
        ("#3b5b8c", "파랑"),  # 중청 데님
        ("#1c2541", "남색"),
        ("#c9a57a", "카멜"),
        ("#5d6140", "카키"),
        ("#722f37", "버건디"),
        ("#efe4c8", "아이보리"),
        ("#f6f1e4", "흰색"),  # 노란 조명 아래의 흰 옷은 흰색으로 본다
        ("#4a4a4d", "회색"),  # 차콜
        ("#2a2a2c", "검정"),  # 빛을 받은 검정 옷
        ("#101012", "검정"),
        ("#fafafa", "흰색"),
        ("#d8c3a5", "베이지"),
        ("#5a3a22", "갈색"),
    ],
)
def test_typical_garment_colors(value, expected):
    assert name_color(hex_to_lab(value)) == expected


def _mask_for(size, box):
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rectangle(box, fill=255)
    return mask


def test_extract_uses_only_masked_pixels():
    image = Image.new("RGB", (300, 300), "#2e7d32")  # 초록 배경
    ImageDraw.Draw(image).rectangle((60, 60, 240, 240), fill="#d32f2f")
    colors = extract_colors(image, _mask_for(image.size, (60, 60, 240, 240)))
    assert [c.name for c in colors] == ["빨강"]
    assert colors[0].ratio == pytest.approx(1.0)


def test_extract_two_tone_ordered_by_area():
    image = Image.new("RGB", (300, 300), "#1f2a44")
    ImageDraw.Draw(image).rectangle((0, 200, 300, 300), fill="#ffffff")
    colors = extract_colors(image, _mask_for(image.size, (0, 0, 299, 299)))
    assert [c.name for c in colors] == ["남색", "흰색"]
    assert colors[0].ratio > colors[1].ratio


def test_shading_on_white_is_one_color_not_gray():
    # 위는 밝고 아래는 그림자가 진 흰 옷
    gradient = np.linspace(245, 175, 300).astype(np.uint8)
    array = np.repeat(gradient[:, None, None], 300, axis=1).repeat(3, axis=2)
    colors = extract_colors(Image.fromarray(array), _mask_for((300, 300), (0, 0, 299, 299)))
    assert [c.name for c in colors] == ["흰색"]


def _stripes(colors_and_shares, size=300):
    """세로로 나뉜 색 띠 이미지. 그림자 진 옷의 밝기 분포를 흉내 낸다."""
    image = Image.new("RGB", (size, size))
    draw, left = ImageDraw.Draw(image), 0
    for color, share in colors_and_shares:
        right = left + round(size * share)
        draw.rectangle((left, 0, right, size), fill=color)
        left = right
    return image


def test_dark_brown_garment_mostly_in_shadow_is_brown_not_black():
    # 실제 착용 사진의 어두운 갈색 후드티에서 나온 분포: 절반 가까이가 그늘이라 거의 검정이다.
    image = _stripes([("#130e0c", 0.47), ("#33271f", 0.25), ("#5e4b39", 0.28)])
    colors = extract_colors(image, _mask_for(image.size, (0, 0, 299, 299)))
    assert [c.name for c in colors] == ["갈색"]


def test_black_garment_with_highlights_stays_black():
    image = _stripes([("#0c0c0c", 0.5), ("#1e1e1e", 0.3), ("#3a3a3a", 0.2)])
    colors = extract_colors(image, _mask_for(image.size, (0, 0, 299, 299)))
    assert [c.name for c in colors] == ["검정"]


def test_dark_navy_garment_in_shadow_is_navy_not_black():
    image = _stripes([("#0a0c14", 0.45), ("#141a2e", 0.3), ("#232d4d", 0.25)])
    colors = extract_colors(image, _mask_for(image.size, (0, 0, 299, 299)))
    assert [c.name for c in colors] == ["남색"]


def test_mid_tone_does_not_bridge_two_different_colors_into_gray():
    # 아이보리와 검정 사이에 주름 그림자 같은 중간 밝기가 끼어 있어도 두 색은 따로 남아야 한다.
    image = _stripes([("#e6dccb", 0.45), ("#8a8378", 0.15), ("#1c1b1a", 0.40)])
    names = [c.name for c in extract_colors(image, _mask_for(image.size, (0, 0, 299, 299)))]
    assert len(names) == 2 and "검정" in names and "회색" not in names


def test_small_accent_is_not_reported_as_second_color():
    image = Image.new("RGB", (300, 300), "#222222")
    ImageDraw.Draw(image).rectangle((0, 0, 30, 30), fill="#f7d038")  # 1% 크기 로고
    colors = extract_colors(image, _mask_for(image.size, (0, 0, 299, 299)))
    assert [c.name for c in colors] == ["검정"]


def test_empty_mask_returns_nothing():
    image = Image.new("RGB", (100, 100), "#ffffff")
    assert extract_colors(image, Image.new("L", image.size, 0)) == []


def test_pale_warm_fabric_is_not_called_gray():
    # 실제 사진의 아이보리 실크에서 나온 값. 채도가 낮아도 밝은 색은 색조가 보인다.
    assert name_color(hex_to_lab("#d2c3b6")) in ("아이보리", "베이지")
    # 그늘진 베이지 코트는 밝기가 내려가도 카멜이 아니라 베이지
    assert name_color(hex_to_lab("#ad9b7a")) == "베이지"


def test_mask_sanity_check():
    from ondo_ai.vision.background import is_plausible_garment

    size = (200, 200)
    assert is_plausible_garment(_mask_for(size, (40, 30, 160, 180)))
    assert not is_plausible_garment(Image.new("L", size, 0))  # 아무것도 못 잡음
    assert not is_plausible_garment(Image.new("L", size, 255))  # 사진 전체를 옷으로 봄
    outline = Image.new("L", size, 0)
    ImageDraw.Draw(outline).rectangle((20, 20, 180, 180), outline=255, width=3)
    assert not is_plausible_garment(outline)  # 윤곽선만 잡힘


def test_transparent_png_is_placed_on_white_not_black():
    from ondo_ai.vision import load_image

    # 투명한 곳의 숨은 RGB가 검정인 PNG (그림 도구가 흔히 이렇게 저장한다)
    rgba = Image.new("RGBA", (120, 120), (0, 0, 0, 0))
    ImageDraw.Draw(rgba).rectangle((30, 30, 90, 90), fill=(211, 47, 47, 255))
    loaded = load_image(rgba)
    assert loaded.mode == "RGB"
    assert loaded.getpixel((5, 5)) == (255, 255, 255)
    assert loaded.getpixel((60, 60)) == (211, 47, 47)

    palette = rgba.convert("P")
    palette.info["transparency"] = palette.getpixel((5, 5))
    assert load_image(palette).getpixel((5, 5)) == (255, 255, 255)


def test_large_photo_is_downscaled_and_rotation_applied():
    from ondo_ai import config
    from ondo_ai.vision import load_image

    big = Image.new("RGB", (4000, 3000), "#808080")
    exif = big.getexif()
    exif[0x0112] = 6  # 휴대폰 세로 촬영: 시계 방향 90도 회전 필요
    big.info["exif"] = exif.tobytes()
    loaded = load_image(big)
    assert max(loaded.size) == config.MAX_IMAGE_SIDE
    assert loaded.height > loaded.width


def test_pair_harmony_rules():
    assert pair_harmony("검정", "빨강") == (1.0, "basic")
    assert pair_harmony("베이지", "갈색")[1] == "tone"
    assert pair_harmony("빨강", "초록")[0] < pair_harmony("빨강", "주황")[0]
    assert pair_harmony(None, "검정")[1] == "unknown"
