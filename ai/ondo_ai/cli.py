"""명령줄 도구.

    ondo-ai analyze 사진.jpg --cutout 결과.png     옷 한 벌 사진 분석
    ondo-ai analyze-outfit 착용.jpg --cutout-dir 폴더   옷이 여러 벌 찍힌 사진을 옷별로 분석
    ondo-ai recommend 요청.json                    추천 (RecommendRequest 형식의 JSON)
    ondo-ai demo --pin 2 --temp 14 --sky 흐림      예시 옷장으로 추천 확인
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .schemas import Place, RecommendRequest, RecommendResult, Sky, Weather


def _print_json(model) -> None:
    print(json.dumps(model.model_dump(mode="json"), ensure_ascii=False, indent=2))


def _print_result(result: RecommendResult) -> None:
    ctx = result.context
    print(f"체감 {ctx.apparent_temp_c}°C, 개인 보정 {ctx.personal_offset_c:+.1f}°C → 기준 {ctx.effective_temp_c}°C")
    for warning in result.warnings:
        print(f"  ! {warning}")
    for item in result.excluded:
        print(f"  - 제외: {item.name} ({item.status.value})")
    for rec in result.recommendations:
        outfit = " + ".join(("[고정] " if item.pinned else "") + item.name for item in rec.items)
        print(f"\n{rec.rank}. {outfit}  ({rec.score}점)")
        print(f"   {rec.reason}")
        for basis in rec.basis:
            print(f"   · {basis.kind}: {basis.text}")
        print("   · 점수: " + ", ".join(f"{k} {v:.2f}" for k, v in rec.breakdown.items()))


def _cmd_analyze(args: argparse.Namespace) -> int:
    from .vision import GarmentAnalyzer

    analyzer = GarmentAnalyzer(device=args.device, remove_background=not args.no_background)
    for image in args.images:
        cutout = None
        if args.cutout:
            target = Path(args.cutout)
            cutout = target if len(args.images) == 1 else target / f"{Path(image).stem}.png"
        print(f"# {image}", file=sys.stderr)
        _print_json(analyzer.analyze(image, cutout_path=cutout, cutout_dir=args.cutout_dir))
    return 0


def _cmd_outfit(args: argparse.Namespace) -> int:
    from .vision import GarmentAnalyzer

    analyzer = GarmentAnalyzer(device=args.device)
    _print_json(analyzer.analyze_outfit(args.image, cutout_dir=args.cutout_dir))
    return 0


def _cmd_recommend(args: argparse.Namespace) -> int:
    from .recommend import recommend

    request = RecommendRequest.model_validate_json(Path(args.request).read_text(encoding="utf-8"))
    _print_json(recommend(request))
    return 0


def _cmd_demo(args: argparse.Namespace) -> int:
    from .recommend import recommend
    from .sample import autumn_wardrobe

    weather = Weather(
        temp_c=args.temp,
        temp_min_c=args.temp_min,
        temp_max_c=args.temp_max,
        sky=Sky(args.sky),
        wind_ms=args.wind,
    )
    request = RecommendRequest(
        wardrobe=autumn_wardrobe(), pinned_id=args.pin, weather=weather, place=Place(args.place), top_k=args.top_k
    )
    result = recommend(request)
    if args.json:
        _print_json(result)
    else:
        _print_result(result)
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")

    parser = argparse.ArgumentParser(prog="ondo-ai", description="온도옷장 AI 모듈")
    sub = parser.add_subparsers(dest="command", required=True)

    analyze = sub.add_parser("analyze", help="옷 사진 분석")
    analyze.add_argument("images", nargs="+")
    analyze.add_argument("--cutout", help="배경 제거 이미지를 저장할 파일 경로 (여러 장이면 폴더)")
    analyze.add_argument("--cutout-dir", help="배경 제거 이미지를 종류별 폴더(상의·하의·겉옷·신발·미분류)로 나눠 저장할 폴더")
    analyze.add_argument("--device", default=None, choices=["auto", "cuda", "cpu"])
    analyze.add_argument("--no-background", action="store_true", help="배경 제거를 건너뛴다 (색상은 비워 둠)")
    analyze.set_defaults(func=_cmd_analyze)

    outfit = sub.add_parser("analyze-outfit", help="옷이 여러 벌 찍힌 사진을 옷별로 나눠 분석")
    outfit.add_argument("image")
    outfit.add_argument("--cutout-dir", help="옷별 배경 제거 이미지를 종류별 폴더(상의·하의·겉옷·신발)로 나눠 저장할 폴더")
    outfit.add_argument("--device", default=None, choices=["auto", "cuda", "cpu"])
    outfit.set_defaults(func=_cmd_outfit)

    rec = sub.add_parser("recommend", help="요청 JSON으로 추천")
    rec.add_argument("request")
    rec.set_defaults(func=_cmd_recommend)

    demo = sub.add_parser("demo", help="예시 가을 옷장으로 추천 확인")
    demo.add_argument("--pin", type=int, default=2, help="고정할 옷 id (기본: 2 베이지 니트)")
    demo.add_argument("--temp", type=float, default=14.0)
    demo.add_argument("--temp-min", type=float, default=None)
    demo.add_argument("--temp-max", type=float, default=None)
    demo.add_argument("--wind", type=float, default=None, help="풍속 m/s")
    demo.add_argument("--sky", default=Sky.CLEAR.value, choices=[s.value for s in Sky])
    demo.add_argument("--place", default=Place.DAILY.value, choices=[p.value for p in Place])
    demo.add_argument("--top-k", type=int, default=3)
    demo.add_argument("--json", action="store_true")
    demo.set_defaults(func=_cmd_demo)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
