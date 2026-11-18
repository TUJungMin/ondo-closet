"""평가용 사진으로 종류 분류 정확도·색상 일치·처리 시간을 잰다. 결과 표를 ai/docs/eval.md에 옮긴다.

정답표(CSV, UTF-8) 형식 — 첫 줄은 제목:

    file,category,color1,color2,condition
    knit_01.jpg,상의,베이지,,일반
    jeans_03.jpg,바지,남색,,복잡한 배경
    shirt_07.jpg,상의,하늘색,흰색,어두운 사진

- category: 상의·바지·스커트·겉옷·신발
- color1/color2: ondo_ai/palette.py의 색 이름. color2는 없으면 비워 둔다.
- condition: 일반 · 복잡한 배경 · 어두운 사진 · 여러 옷  (구분해서 집계)

평가용 사진은 문구·기준값을 조정할 때 본 사진과 섞지 않는다. (CLAUDE.md 6장)

    python scripts/evaluate.py 평가폴더 --labels 평가폴더/labels.csv
    python scripts/evaluate.py 평가폴더 --labels ... --model fashion-clip      # 비교 기준선
    python scripts/evaluate.py 평가폴더 --labels ... --classify-on original   # 배경 제거 없이 분류
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path

from ondo_ai import config
from ondo_ai.palette import COLOR_NAMES
from ondo_ai.schemas import Category
from ondo_ai.vision import GarmentAnalyzer
from ondo_ai.vision.classifier import build_classifier

_CATEGORIES = {c.value for c in Category}


def _percent(hit: int, total: int) -> str:
    return f"{hit}/{total} ({100 * hit / total:.0f}%)" if total else "-"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder")
    parser.add_argument("--labels", required=True)
    parser.add_argument("--model", default="fashion-siglip", choices=["fashion-siglip", "fashion-clip"])
    parser.add_argument("--classify-on", default=None, choices=["cutout", "original"])
    parser.add_argument("--device", default=None, choices=["auto", "cuda", "cpu"])
    args = parser.parse_args()
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")

    with open(args.labels, encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        if row["category"] not in _CATEGORIES:
            raise SystemExit(f"{row['file']}: 알 수 없는 종류 '{row['category']}'")
        for key in ("color1", "color2"):
            if row.get(key) and row[key] not in COLOR_NAMES:
                raise SystemExit(f"{row['file']}: 색 이름표에 없는 색 '{row[key]}'")

    device = config.resolve_device(args.device)
    analyzer = GarmentAnalyzer(
        device=device, classifier=build_classifier(device, args.model), classify_on=args.classify_on
    )
    analyzer.warmup()
    analyzer.analyze(Path(args.folder) / rows[0]["file"])  # 첫 요청은 느리므로 시간 집계에서 뺀다

    stats = defaultdict(lambda: defaultdict(int))  # condition -> 집계
    times: list[float] = []
    mistakes: list[str] = []
    for row in rows:
        condition = row.get("condition") or "일반"
        result = analyzer.analyze(Path(args.folder) / row["file"])
        times.append(result.timings_ms.get("전체", 0.0))
        predicted = [c.name for c in result.colors]
        expected = [c for c in (row["color1"], row.get("color2")) if c]
        top_guess = result.category.candidates[0].label if result.category.candidates else None

        for scope in (condition, "전체"):
            s = stats[scope]
            s["n"] += 1
            s["category_shown"] += result.category.value is not None
            s["category_right"] += result.category.value == row["category"]
            s["category_wrong"] += result.category.value not in (None, row["category"])
            s["category_top1"] += top_guess == row["category"]
            s["color_primary"] += bool(predicted) and predicted[0] == row["color1"]
            s["color_any"] += bool(set(predicted) & set(expected))

        if result.category.value != row["category"] or not (predicted and predicted[0] == row["color1"]):
            shown = result.category.value or f"비움(1순위 {top_guess})"
            mistakes.append(
                f"| {row['file']} | {condition} | {row['category']} → {shown} "
                f"({result.category.confidence:.2f}) | {'·'.join(expected)} → {'·'.join(predicted) or '없음'} |"
            )

    print(f"모델: {analyzer.classifier.model_id} | 분류 입력: {analyzer.classify_on} | 장치: {device} | {len(rows)}장")
    print()
    print("| 조건 | 장수 | 종류 정답(제안한 것 중) | 종류 틀리게 제안 | 종류 비움 | 1순위 후보 정답 | 대표색 일치 | 색 하나 이상 일치 |")
    print("|---|---:|---|---|---|---|---|---|")
    for scope in [k for k in stats if k != "전체"] + ["전체"]:
        s = stats[scope]
        n = s["n"]
        print(
            f"| {scope} | {n} | {_percent(s['category_right'], s['category_shown'])} "
            f"| {_percent(s['category_wrong'], n)} | {_percent(n - s['category_shown'], n)} "
            f"| {_percent(s['category_top1'], n)} | {_percent(s['color_primary'], n)} | {_percent(s['color_any'], n)} |"
        )
    print()
    ordered = sorted(times)
    p95 = ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))]
    print(f"사진당 처리 시간: 평균 {statistics.mean(times):.0f} ms, 중앙값 {statistics.median(times):.0f} ms, 95% {p95:.0f} ms")
    if mistakes:
        print()
        print("| 파일 | 조건 | 종류 (정답 → 결과, 확신도) | 색 (정답 → 결과) |")
        print("|---|---|---|---|")
        print("\n".join(mistakes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
