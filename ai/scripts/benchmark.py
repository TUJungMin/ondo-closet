"""사진당 처리 시간을 잰다. 배포 서버에서 한 번 돌려 ai/docs/eval.md에 옮겨 적는다.

    python scripts/benchmark.py 사진폴더 --device cpu
    python scripts/benchmark.py 사진1.jpg 사진2.jpg --device cuda --repeat 3

모델 로드 시간, 첫 요청(워밍업 포함) 시간, 그 뒤 단계별 평균 시간을 따로 보여준다.
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

from ondo_ai.vision import GarmentAnalyzer

_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def collect(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            files.extend(sorted(p for p in path.iterdir() if p.suffix.lower() in _EXTENSIONS))
        else:
            files.append(path)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--device", default=None, choices=["auto", "cuda", "cpu"])
    parser.add_argument("--repeat", type=int, default=2, help="사진 묶음을 몇 번 반복할지")
    args = parser.parse_args()
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")

    files = collect(args.paths)
    if not files:
        print("사진이 없습니다.")
        return 1

    analyzer = GarmentAnalyzer(device=args.device)
    started = time.perf_counter()
    analyzer.warmup()
    load_s = time.perf_counter() - started

    started = time.perf_counter()
    analyzer.analyze(files[0])
    first_s = time.perf_counter() - started

    stages: dict[str, list[float]] = {}
    problems: dict[str, int] = {}
    for _ in range(args.repeat):
        for path in files:
            result = analyzer.analyze(path)
            for stage, ms in result.timings_ms.items():
                stages.setdefault(stage, []).append(ms)
            for warning in result.warnings:
                problems[warning] = problems.get(warning, 0) + 1

    print(f"장치: {analyzer.device} | 사진 {len(files)}장 × {args.repeat}회")
    print(f"모델 로드(빈 사진 1회 추론 포함): {load_s:.1f}초 | 그 뒤 첫 요청: {first_s * 1000:.0f} ms")
    # 단계가 실패하면 시간이 짧게 찍히므로, 경고를 꼭 같이 본다.
    for warning, count in problems.items():
        print(f"  ! {count}회: {warning}")
    print("| 단계 | 평균 ms | 중앙값 ms | 최대 ms |")
    print("|---|---:|---:|---:|")
    for stage in ("배경 제거", "색상", "분류", "전체"):
        values = stages.get(stage, [])
        if values:
            print(f"| {stage} | {statistics.mean(values):.0f} | {statistics.median(values):.0f} | {max(values):.0f} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
