"""평가용 사진으로 종류 분류 정확도·색상 일치·처리 시간을 잰다. 결과 표를 ai/docs/eval.md에 옮긴다.

1) 옷 한 벌 사진 — 정답표(CSV, UTF-8) 형식. 첫 줄은 제목:

    file,category,color1,color2,condition
    knit_01.jpg,상의,베이지,,일반
    jeans_03.jpg,바지,남색,,복잡한 배경
    shirt_07.jpg,상의,하늘색,흰색,어두운 사진

- category: 상의·바지·스커트·겉옷·신발
- color1/color2: ondo_ai/palette.py의 색 이름. color2는 없으면 비워 둔다.
- condition: 일반 · 복잡한 배경 · 어두운 사진 · 여러 옷  (구분해서 집계)

    python scripts/evaluate.py 평가폴더 --labels 평가폴더/labels.csv
    python scripts/evaluate.py 평가폴더 --labels ... --model fashion-clip      # 비교 기준선
    python scripts/evaluate.py 평가폴더 --labels ... --classify-on original   # 배경 제거 없이 분류

2) 착용 사진(옷이 여러 벌 찍힌 사진) — 정답표 형식. 사진에 보이는 옷장 종류를 ';'로 이어 적는다:

    file,expected,condition
    outfit_01.jpg,"상의;바지;신발",일반
    outfit_02.jpg,"상의;겉옷;스커트;신발",복잡한 배경

- expected: 찾아야 할 옷의 종류. 같은 종류가 두 벌이면 두 번 적는다. 가방·모자·원피스는 적지 않는다.
- condition: 없어도 된다(없으면 '일반').

    python scripts/evaluate.py 평가폴더 --outfit-labels 평가폴더/outfit_labels.csv

  재는 것: 재현율(찾아야 할 옷 중 찾은 비율), 잘못 찾은 옷 수, 찾은 옷의 종류 정확도, 사진당 시간.
  정답표에 옷의 위치는 없으므로 부위(상체·하체·발)별 개수로 맞춘다. 같은 부위에서 엉뚱한 옷을 잡고
  진짜 옷을 놓친 경우는 '찾음'으로 세어질 수 있으니, 아래에 찍히는 사진별 결과를 눈으로도 확인한다.

평가용 사진은 문구·기준값을 조정할 때 본 사진과 섞지 않는다. (CLAUDE.md 6장)
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ondo_ai import config  # noqa: E402
from ondo_ai.palette import COLOR_NAMES  # noqa: E402
from ondo_ai.schemas import Category  # noqa: E402
from ondo_ai.vision.detect import FEET, GARMENT_LABELS, LOWER, UPPER  # noqa: E402

_CATEGORIES = {c.value for c in Category}
_PART_OF_CATEGORY = {"상의": UPPER, "겉옷": UPPER, "바지": LOWER, "스커트": LOWER, "신발": FEET}


def _percent(hit: int, total: int) -> str:
    return f"{hit}/{total} ({100 * hit / total:.0f}%)" if total else "-"


def _time_line(times: list[float]) -> str:
    ordered = sorted(times)
    p95 = ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))]
    return f"사진당 처리 시간: 평균 {statistics.mean(times):.0f} ms, 중앙값 {statistics.median(times):.0f} ms, 95% {p95:.0f} ms"


def _read_rows(path: str) -> list[dict[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SystemExit(f"{path}: 정답표가 비어 있습니다.")
    return rows


# ------------------------------------------------------------------ 착용 사진 채점


@dataclass
class OutfitScore:
    """착용 사진 한 장의 채점 결과."""

    expected: int  # 찾아야 할 옷
    found: int  # 그중 찾은 옷
    false_finds: int  # 잘못 찾은 옷 (정답에 없는데 찾은 것)
    category_right: int  # 찾은 옷 중 종류까지 맞은 것
    missed: list[str]  # 놓친 옷의 종류


def parse_expected(text: str) -> list[str]:
    """ "상의;바지;신발" → ["상의", "바지", "신발"]. 모르는 종류가 있으면 ValueError."""
    names = [name.strip() for name in text.split(";") if name.strip()]
    if not names:
        raise ValueError("찾아야 할 옷이 비어 있습니다")
    for name in names:
        if name not in _PART_OF_CATEGORY:
            raise ValueError(f"알 수 없는 종류 '{name}'")
    return names


def score_outfit(expected: Sequence[str], found: Sequence[tuple[str, Optional[str]]]) -> OutfitScore:
    """정답 종류 목록과 찾은 옷 목록 [(부위, 제안한 종류 또는 None)]을 부위별 개수로 맞춘다.

    부위(상체·하체·발)마다 '정답 수'와 '찾은 수' 중 작은 쪽만큼을 찾은 것으로 본다.
    남는 정답은 놓친 옷, 남는 검출은 잘못 찾은 옷이다. 찾은 옷의 종류는 같은 부위 안에서 맞춰 본다.
    """
    score = OutfitScore(expected=len(expected), found=0, false_finds=0, category_right=0, missed=[])
    for part in (UPPER, LOWER, FEET):
        want = Counter(name for name in expected if _PART_OF_CATEGORY[name] == part)
        got = [category for found_part, category in found if found_part == part]
        matched = min(sum(want.values()), len(got))
        right = sum((want & Counter(c for c in got if c is not None)).values())
        score.found += matched
        score.false_finds += len(got) - matched
        score.category_right += min(right, matched)
        # 놓친 옷: 종류까지 맞은 것을 지우고 남은 정답 가운데 (찾은 수 - 맞은 수)벌은 '종류만 틀리게 찾음'이다.
        # 남은 정답의 종류가 섞여 있으면 어느 쪽을 놓쳤는지 알 수 없으므로 부위와 벌 수만 적는다.
        left = sorted((want - Counter(c for c in got if c is not None)).elements())
        n_missed = len(left) - (matched - right)
        if n_missed and (matched == right or len(set(left)) == 1):
            score.missed.extend(left[:n_missed])
        elif n_missed:
            score.missed.append(f"{part} {n_missed}벌")
    return score


def evaluate_outfits(args: argparse.Namespace, analyzer, device: str) -> None:
    rows = _read_rows(args.outfit_labels)
    for row in rows:
        try:
            row["_expected"] = parse_expected(row.get("expected") or "")  # type: ignore[assignment]
        except ValueError as error:
            raise SystemExit(f"{row.get('file')}: {error}") from None

    analyzer.warmup(outfit=True)
    analyzer.analyze_outfit(Path(args.folder) / rows[0]["file"])  # 첫 요청은 느리므로 시간 집계에서 뺀다

    stats = defaultdict(lambda: defaultdict(int))
    times: list[float] = []
    details: list[str] = []
    for row in rows:
        condition = row.get("condition") or "일반"
        expected: list[str] = row["_expected"]  # type: ignore[assignment]
        result = analyzer.analyze_outfit(Path(args.folder) / row["file"])
        times.append(result.timings_ms.get("전체", 0.0))
        found = [(GARMENT_LABELS[item.detector_label][1], item.analysis.category.value) for item in result.items]
        score = score_outfit(expected, found)

        for scope in (condition, "전체"):
            s = stats[scope]
            s["n"] += 1
            s["expected"] += score.expected
            s["found"] += score.found
            s["false"] += score.false_finds
            s["category_right"] += score.category_right
            s["complete"] += score.found == score.expected and score.false_finds == 0

        shown = "·".join(category or "비움" for _, category in found) or "없음"
        note = []
        if score.missed:
            note.append("놓침 " + "·".join(score.missed))
        if score.false_finds:
            note.append(f"잘못 찾음 {score.false_finds}")
        if score.category_right < score.found:
            note.append(f"종류 틀림 {score.found - score.category_right}")
        if result.skipped:
            note.append("제외 " + "·".join(result.skipped))
        details.append(f"| {row['file']} | {condition} | {'·'.join(expected)} | {shown} | {', '.join(note) or '모두 맞음'} |")

    print(f"착용 사진 | 분류 모델: {analyzer.classifier.model_id} | 분류 입력: {analyzer.classify_on} | 장치: {device} | {len(rows)}장")
    print()
    print("| 조건 | 장수 | 찾아야 할 옷 | 찾은 옷 (재현율) | 잘못 찾은 옷 | 찾은 옷의 종류 정답 | 빠짐·잘못 없이 나눈 사진 |")
    print("|---|---:|---:|---|---:|---|---|")
    for scope in [k for k in stats if k != "전체"] + ["전체"]:
        s = stats[scope]
        print(
            f"| {scope} | {s['n']} | {s['expected']} | {_percent(s['found'], s['expected'])} | {s['false']} "
            f"| {_percent(s['category_right'], s['found'])} | {_percent(s['complete'], s['n'])} |"
        )
    print()
    print(_time_line(times))
    print()
    print("| 파일 | 조건 | 정답 | 찾은 옷 (위에서 아래) | 판정 |")
    print("|---|---|---|---|---|")
    print("\n".join(details))


# ------------------------------------------------------------------ 옷 한 벌 사진


def evaluate_single(args: argparse.Namespace, analyzer, device: str) -> None:
    rows = _read_rows(args.labels)
    for row in rows:
        if row["category"] not in _CATEGORIES:
            raise SystemExit(f"{row['file']}: 알 수 없는 종류 '{row['category']}'")
        for key in ("color1", "color2"):
            if row.get(key) and row[key] not in COLOR_NAMES:
                raise SystemExit(f"{row['file']}: 색 이름표에 없는 색 '{row[key]}'")

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
    print(_time_line(times))
    if mistakes:
        print()
        print("| 파일 | 조건 | 종류 (정답 → 결과, 확신도) | 색 (정답 → 결과) |")
        print("|---|---|---|---|")
        print("\n".join(mistakes))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder")
    parser.add_argument("--labels", help="옷 한 벌 사진 정답표")
    parser.add_argument("--outfit-labels", help="착용 사진(옷이 여러 벌) 정답표")
    parser.add_argument("--model", default="fashion-siglip", choices=["fashion-siglip", "fashion-clip"])
    parser.add_argument("--classify-on", default=None, choices=["cutout", "original"])
    parser.add_argument("--device", default=None, choices=["auto", "cuda", "cpu"])
    args = parser.parse_args()
    if not args.labels and not args.outfit_labels:
        parser.error("--labels 나 --outfit-labels 중 하나는 있어야 합니다.")
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")

    from ondo_ai.vision import GarmentAnalyzer
    from ondo_ai.vision.classifier import build_classifier

    device = config.resolve_device(args.device)
    analyzer = GarmentAnalyzer(
        device=device, classifier=build_classifier(device, args.model), classify_on=args.classify_on
    )
    if args.labels:
        evaluate_single(args, analyzer, device)
    if args.outfit_labels:
        if args.labels:
            print()
        evaluate_outfits(args, analyzer, device)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
