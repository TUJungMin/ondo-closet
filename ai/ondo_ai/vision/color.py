"""대표색 계산. 모델에게 묻지 않고 옷 픽셀에서 직접 구한다.

배경 제거 마스크 안쪽 픽셀 → Lab 색공간 k-means → 음영만 다른 묶음 합치기 → 색 이름표에서 가장 가까운 이름.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from PIL import Image, ImageFilter

from .. import config
from ..palette import PALETTE
from ..schemas import ColorInfo

_K = 5
_WORK_SIDE = 512
_MAX_SAMPLES = 12_000
_MIN_PIXELS = 200

# 같은 색의 밝고 어두운 부분(주름·그림자)으로 보는 범위
_SHADE_AB = 18.0
_SHADE_L = 40.0

# 빛을 받은 쪽이 묶음의 이만큼은 되어야 대표값 계산에 쓴다 (작은 반사광에 끌려가지 않게)
_LIT_MIN_SHARE = 0.10

# 무채색 판정
_ACHROMATIC_CHROMA = 7.0
_BLACK_L = 26.0
_WHITE_L = 82.0

_WHITE_POINT = np.array([0.95047, 1.0, 1.08883])
_RGB_TO_XYZ = np.array(
    [
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041],
    ]
)
_XYZ_TO_RGB = np.linalg.inv(_RGB_TO_XYZ)


def srgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """(..., 3) uint8 sRGB → CIE Lab (D65)."""
    c = np.asarray(rgb, dtype=np.float64) / 255.0
    linear = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    xyz = linear @ _RGB_TO_XYZ.T / _WHITE_POINT
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], axis=-1)


def lab_to_srgb(lab: np.ndarray) -> np.ndarray:
    lab = np.asarray(lab, dtype=np.float64)
    fy = (lab[..., 0] + 16) / 116
    fx = fy + lab[..., 1] / 500
    fz = fy - lab[..., 2] / 200
    f = np.stack([fx, fy, fz], axis=-1)
    xyz = np.where(f**3 > 216 / 24389, f**3, (116 * f - 16) * 27 / 24389) * _WHITE_POINT
    linear = np.clip(xyz @ _XYZ_TO_RGB.T, 0.0, 1.0)
    srgb = np.where(linear <= 0.0031308, 12.92 * linear, 1.055 * linear ** (1 / 2.4) - 0.055)
    return np.clip(np.round(srgb * 255), 0, 255).astype(np.uint8)


def hex_to_lab(value: str) -> np.ndarray:
    value = value.lstrip("#")
    return srgb_to_lab(np.array([int(value[i : i + 2], 16) for i in (0, 2, 4)], dtype=np.uint8))


def lab_to_hex(lab: np.ndarray) -> str:
    r, g, b = (int(v) for v in lab_to_srgb(lab))
    return f"#{r:02x}{g:02x}{b:02x}"


def ciede2000(lab1: np.ndarray, lab2: np.ndarray, k_l: float = 1.0) -> np.ndarray:
    """CIEDE2000 색차. 두 입력은 (..., 3)이고 서로 브로드캐스트된다.

    k_l을 2로 주면 밝기 차이를 절반만 본다. (섬유 분야에서 쓰는 2:1:1 가중)
    """
    l1, a1, b1 = (np.asarray(lab1, dtype=np.float64)[..., i] for i in range(3))
    l2, a2, b2 = (np.asarray(lab2, dtype=np.float64)[..., i] for i in range(3))
    c_bar = (np.hypot(a1, b1) + np.hypot(a2, b2)) / 2
    g = 0.5 * (1 - np.sqrt(c_bar**7 / (c_bar**7 + 25.0**7)))
    a1p, a2p = (1 + g) * a1, (1 + g) * a2
    c1p, c2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360
    gray = (c1p * c2p) == 0

    dl = l2 - l1
    dc = c2p - c1p
    dh = h2p - h1p
    dh = np.where(gray, 0.0, np.where(np.abs(dh) <= 180, dh, np.where(dh > 180, dh - 360, dh + 360)))
    dbig_h = 2 * np.sqrt(c1p * c2p) * np.sin(np.radians(dh / 2))

    l_bar = (l1 + l2) / 2
    c_barp = (c1p + c2p) / 2
    h_sum = h1p + h2p
    h_bar = np.where(
        gray,
        h_sum,
        np.where(np.abs(h1p - h2p) <= 180, h_sum / 2, np.where(h_sum < 360, (h_sum + 360) / 2, (h_sum - 360) / 2)),
    )
    t = (
        1
        - 0.17 * np.cos(np.radians(h_bar - 30))
        + 0.24 * np.cos(np.radians(2 * h_bar))
        + 0.32 * np.cos(np.radians(3 * h_bar + 6))
        - 0.20 * np.cos(np.radians(4 * h_bar - 63))
    )
    d_theta = 30 * np.exp(-(((h_bar - 275) / 25) ** 2))
    r_c = 2 * np.sqrt(c_barp**7 / (c_barp**7 + 25.0**7))
    s_l = 1 + 0.015 * (l_bar - 50) ** 2 / np.sqrt(20 + (l_bar - 50) ** 2)
    s_c = 1 + 0.045 * c_barp
    s_h = 1 + 0.015 * c_barp * t
    r_t = -np.sin(np.radians(2 * d_theta)) * r_c
    return np.sqrt(
        (dl / (k_l * s_l)) ** 2 + (dc / s_c) ** 2 + (dbig_h / s_h) ** 2 + r_t * (dc / s_c) * (dbig_h / s_h)
    )


_SWATCH_NAMES: list[str] = [c.name for c in PALETTE for _ in c.swatches]
_SWATCH_LAB: np.ndarray = np.stack([hex_to_lab(s) for c in PALETTE for s in c.swatches])


def _is_achromatic(lightness: float, chroma: float) -> bool:
    if lightness >= 88.0:
        return chroma < 8.0  # 거의 흰색이면 조명 색이 조금 묻어도 무채색으로 본다
    if lightness >= 60.0:
        return chroma < 6.0  # 밝은 색은 옅은 색조도 눈에 띈다 (아이보리·베이지)
    return chroma < _ACHROMATIC_CHROMA


def name_color(lab: np.ndarray) -> str:
    """Lab 한 점에 색 이름을 붙인다. 무채색은 밝기로 먼저 가르고, 나머지는 가장 가까운 견본의 이름.

    견본과의 거리는 밝기 차이를 절반만 본다. 사진 속 옷은 조명·그림자에 따라 밝기가 가장 크게 흔들리기 때문이다.
    """
    lightness, a, b = (float(v) for v in lab)
    chroma = float(np.hypot(a, b))
    if lightness < 6.0:  # 이 밝기에서는 색조를 구분할 수 없다
        return "검정"
    if _is_achromatic(lightness, chroma):
        if lightness < _BLACK_L:
            return "검정"
        if lightness > _WHITE_L:
            return "흰색"
        return "회색"
    return _SWATCH_NAMES[int(ciede2000(np.asarray(lab), _SWATCH_LAB, k_l=2.0).argmin())]


def kmeans(points: np.ndarray, k: int, iterations: int = 20, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """k-means++ 초기화 k-means. (중심, 묶음별 개수)를 돌려준다. 시드를 고정해 결과가 매번 같다."""
    rng = np.random.default_rng(seed)
    centers = [points[rng.integers(len(points))]]
    for _ in range(1, k):
        d2 = np.min(((points[:, None, :] - np.array(centers)[None]) ** 2).sum(-1), axis=1)
        if d2.sum() <= 1e-9:
            break
        centers.append(points[rng.choice(len(points), p=d2 / d2.sum())])
    centers_arr = np.array(centers, dtype=np.float64)
    labels = np.zeros(len(points), dtype=np.int64)
    for _ in range(iterations):
        labels = ((points[:, None, :] - centers_arr[None]) ** 2).sum(-1).argmin(1)
        updated = np.array(
            [points[labels == j].mean(0) if np.any(labels == j) else centers_arr[j] for j in range(len(centers_arr))]
        )
        if np.allclose(updated, centers_arr, atol=0.05):
            centers_arr = updated
            break
        centers_arr = updated
    return centers_arr, np.bincount(labels, minlength=len(centers_arr))


@dataclass
class _Group:
    seed: np.ndarray  # 이 묶음의 기준 색 (가장 큰 구성원의 Lab)
    members: list[tuple[np.ndarray, float]] = field(default_factory=list)  # (중심 Lab, 비율)

    @property
    def weight(self) -> float:
        return sum(w for _, w in self.members)

    @property
    def center(self) -> np.ndarray:
        return sum(c * w for c, w in self.members) / self.weight  # type: ignore[return-value]

    def representative(self) -> np.ndarray:
        """이름과 견본색에 쓰는 대표값: 묶음 평균과 '빛을 받은 쪽' 평균의 중간.

        주름·그림자 진 부분은 밝기가 내려가고 색조도 거의 사라진다. 옷의 실제 색은 빛을 받은 쪽에
        드러나므로 그쪽으로 절반 당긴다. 평균만 쓰면 흰 옷이 회색으로, 어두운 갈색·카키·남색 옷이
        검정으로 읽힌다.

        예외: 밝은 쪽에도 색조가 없는 어두운 옷은 당기지 않는다. 검정 옷의 밝은 부분은 광택일 뿐이라,
        당기면 검정이 회색으로 읽힌다.
        """
        center = self.center
        lit = [(c, w) for c, w in self.members if c[0] >= center[0]]
        lit_weight = sum(w for _, w in lit)
        if lit_weight < _LIT_MIN_SHARE * self.weight:
            return center
        lit_mean = sum(c * w for c, w in lit) / lit_weight
        if center[0] < 60.0 and float(np.hypot(lit_mean[1], lit_mean[2])) < _ACHROMATIC_CHROMA:
            return center
        return 0.5 * center + 0.5 * lit_mean


def _same_shade(a: np.ndarray, b: np.ndarray) -> bool:
    return float(np.hypot(a[1] - b[1], a[2] - b[2])) < _SHADE_AB and abs(float(a[0] - b[0])) < _SHADE_L


def _garment_pixels(image: Image.Image, mask: Optional[Image.Image]) -> np.ndarray:
    image = image.convert("RGB")
    if max(image.size) > _WORK_SIDE:  # 대표색에는 큰 해상도가 필요 없다
        scale = _WORK_SIDE / max(image.size)
        image = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.BILINEAR)
    rgb = np.asarray(image)
    if mask is None:
        return rgb.reshape(-1, 3)
    if mask.size != image.size:
        mask = mask.resize(image.size, Image.BILINEAR)
    # 가장자리는 배경색이 섞이므로 마스크를 조금 깎아 안쪽만 쓴다.
    size = max(3, (min(image.size) // 150) | 1)
    inner = np.asarray(mask.filter(ImageFilter.MinFilter(size))) > 127
    if inner.sum() < _MIN_PIXELS:
        inner = np.asarray(mask) > 127
    return rgb[inner]


def extract_colors(image: Image.Image, mask: Optional[Image.Image] = None, max_colors: int = 2) -> list[ColorInfo]:
    """옷 픽셀에서 대표색을 최대 max_colors개 뽑는다. mask는 옷 영역이 밝은 'L' 이미지."""
    pixels = _garment_pixels(image, mask)
    if len(pixels) < _MIN_PIXELS:
        return []
    if len(pixels) > _MAX_SAMPLES:
        pixels = pixels[np.random.default_rng(0).choice(len(pixels), _MAX_SAMPLES, replace=False)]

    centers, counts = kmeans(srgb_to_lab(pixels), _K)
    ratios = counts / counts.sum()

    # 큰 묶음부터 '기준 색'으로 삼고, 나머지는 음영만 다른 기준 색이 있으면 그쪽에 붙인다.
    # 기준 색과 직접 비교해야 한다. 합쳐진 평균과 비교하면 중간 밝기 묶음이 다리가 되어
    # 아이보리와 검정처럼 전혀 다른 두 색이 한 덩어리(회색)로 이어 붙는다.
    groups: list[_Group] = []
    for index in np.argsort(ratios)[::-1]:
        if ratios[index] <= 0:
            continue
        center = centers[index]
        near = [g for g in groups if _same_shade(g.seed, center)]
        if near:
            home = min(near, key=lambda g: abs(float(g.seed[0] - center[0])))
        else:
            home = _Group(seed=center)
            groups.append(home)
        home.members.append((center, float(ratios[index])))

    named: dict[str, _Group] = {}
    for group in groups:
        name = name_color(group.representative())
        if name in named:
            named[name].members.extend(group.members)
        else:
            named[name] = group

    ranked = sorted(named.items(), key=lambda kv: kv[1].weight, reverse=True)
    result: list[ColorInfo] = []
    for position, (name, group) in enumerate(ranked[:max_colors]):
        if position > 0 and group.weight < config.SECOND_COLOR_MIN_RATIO:
            break
        result.append(ColorInfo(name=name, hex=lab_to_hex(group.representative()), ratio=round(group.weight, 3)))
    return result
