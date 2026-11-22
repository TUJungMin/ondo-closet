"""추천 한 번(/ai/recommend)에 걸리는 시간을 잰다. 모델을 쓰지 않으므로 GPU와 무관하다.

    python scripts/bench_recommend.py                               # 엔진만 (함수 호출)
    python scripts/bench_recommend.py --url http://127.0.0.1:8000   # 띄워 둔 서버로 HTTP 왕복까지

백엔드는 고정 옷이 없을 때 상의 최대 5벌을 차례로 고정해 /ai/recommend 를 5번 부른다.
그래서 '한 번'과 '상의 5벌 연속'을 함께 잰다. 요청에는 백엔드가 실제로 보내는 필드만 넣는다
(status · wear_history · rejections 없음 → 옷장의 모든 옷이 조합 대상이 되는 가장 느린 경우).
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ondo_ai.recommend import recommend  # noqa: E402
from ondo_ai.sample import autumn_wardrobe  # noqa: E402
from ondo_ai.schemas import SLOT_OF, Category, Garment, RecommendRequest, Status, Style, Weather  # noqa: E402

_COLORS = ["검정", "흰색", "회색", "아이보리", "베이지", "카멜", "갈색", "카키", "남색", "파랑", "하늘색", "버건디"]
_STYLES = list(Style)
# 12벌: 백엔드 게스트 옷장과 같은 구성 (상의 4 · 바지 3 · 겉옷 3 · 신발 2)
_SMALL = {Category.TOP: 4, Category.PANTS: 3, Category.OUTER: 3, Category.SHOES: 2}
# 50벌: 상의 16 · 바지 9 · 스커트 3 · 겉옷 12 · 신발 10
_LARGE = {Category.TOP: 16, Category.PANTS: 9, Category.SKIRT: 3, Category.OUTER: 12, Category.SHOES: 10}


def build_wardrobe(counts: dict[Category, int]) -> list[Garment]:
    """예시 옷장(30벌)에서 종류별로 필요한 만큼 가져오고, 모자라면 색·보온성·스타일을 돌려 가며 채운다."""
    base = [g.model_copy(update={"status": Status.AVAILABLE}) for g in autumn_wardrobe()]
    wardrobe: list[Garment] = []
    next_id = 1000
    for category, count in counts.items():
        same = [g for g in base if g.category == category]
        wardrobe.extend(same[:count])
        for i in range(max(0, count - len(same))):
            next_id += 1
            color = _COLORS[(next_id * 7 + i) % len(_COLORS)]
            wardrobe.append(
                Garment(
                    id=next_id,
                    name=f"{color} {category.value} {i + 1}",
                    category=category,
                    colors=[color],
                    warmth=1 + (next_id + i) % 5,
                    style=_STYLES[(next_id + i) % len(_STYLES)],
                    waterproof=category in (Category.OUTER, Category.SHOES) and i % 3 == 0,
                    grip=category == Category.SHOES and i % 2 == 0,
                )
            )
    return wardrobe


def backend_payload(wardrobe: list[Garment], pinned_id, top_k: int) -> dict:
    """백엔드 AiRecommend.Request 와 같은 모양."""
    return {
        "wardrobe": [
            {
                "id": g.id,
                "name": g.name,
                "category": g.category.value,
                "colors": g.colors[:1],
                "warmth": g.warmth,
                "style": g.style.value if g.style else None,
                "waterproof": g.waterproof,
                "grip": g.grip,
            }
            for g in wardrobe
        ],
        "pinned_id": pinned_id,
        "weather": {"temp_c": 8, "feels_like_c": 5, "temp_min_c": 3, "temp_max_c": 12, "sky": "맑음", "precip_prob": 0.1, "wind_ms": 3},
        "place": "일상",
        "top_k": top_k,
    }


def combos(wardrobe: list[Garment], pinned: Garment) -> int:
    """고정 옷이 정해졌을 때 엔진이 점수를 매기는 조합 수 (겉옷은 '없음' 포함)."""
    per_slot = {"상의": 0, "하의": 0, "겉옷": 1, "신발": 0}
    for g in wardrobe:
        per_slot[SLOT_OF[g.category]] += 1
    per_slot[SLOT_OF[pinned.category]] = 1
    total = 1
    for n in per_slot.values():
        total *= max(n, 1)
    return total


def timed(call, repeat: int) -> tuple[float, float]:
    """(중앙값, 최댓값) 밀리초."""
    call()  # 첫 호출의 준비 시간은 뺀다
    samples = []
    for _ in range(repeat):
        start = time.perf_counter()
        call()
        samples.append((time.perf_counter() - start) * 1000)
    return statistics.median(samples), max(samples)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", help="띄워 둔 AI 서버 주소. 주면 HTTP 왕복 시간도 잰다")
    parser.add_argument("--repeat", type=int, default=20)
    args = parser.parse_args()

    client = None
    if args.url:
        import httpx

        client = httpx.Client(base_url=args.url, timeout=30)

    print("| 옷장 | 고정 옷 | top_k | 조합 수 | 엔진만 중앙값(최대) | HTTP 왕복 중앙값(최대) |")
    print("|---|---|---:|---:|---:|---:|")
    for label, counts in (("12벌", _SMALL), ("50벌", _LARGE)):
        wardrobe = build_wardrobe(counts)
        tops = [g for g in wardrobe if g.category == Category.TOP]
        shoes = next(g for g in wardrobe if g.category == Category.SHOES)
        # 신발 고정이 조합 수가 가장 많다(상의 × 하의 × 겉옷). top_k 10은 백엔드가 요청하는 최댓값.
        cases = [("상의 1벌", [tops[0]], 3), ("신발 1벌 (조합 최다)", [shoes], 3), ("신발 1벌 (조합 최다)", [shoes], 10), ("상의 5벌 연속", tops[:5], 3)]
        for name, pins, top_k in cases:
            payloads = [backend_payload(wardrobe, pin.id, top_k) for pin in pins]
            requests = [RecommendRequest(**p) for p in payloads]

            def run_engine() -> None:
                for request in requests:
                    recommend(request)

            engine_med, engine_max = timed(run_engine, args.repeat)
            http = "—"
            if client is not None:

                def run_http() -> None:
                    for payload in payloads:
                        client.post("/ai/recommend", json=payload).raise_for_status()

                http_med, http_max = timed(run_http, args.repeat)
                http = f"{http_med:.1f} ms ({http_max:.1f})"
            n = sum(combos(wardrobe, pin) for pin in pins)
            print(f"| {label} | {name} | {top_k} | {n:,} | {engine_med:.1f} ms ({engine_max:.1f}) | {http} |")


if __name__ == "__main__":
    main()
