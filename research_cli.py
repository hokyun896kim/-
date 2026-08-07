#!/usr/bin/env python3
"""점수 검증 CLI — 이벤트 스터디를 돌려 예측력을 측정한다.

이 시스템의 점수가 실제로 미래 수익률을 예측하는지 재는 도구다.
결과가 나오기 전까지 스크리너 랭킹과 '적극 매수' 배너는 근거 없는 숫자다.

사용 예:
  # 시총 상위 60종목, 최근 5년, 20·60일 후 초과수익률
  python research_cli.py --top 60 --period 5y

  # 추세 vs 역추세 중 어느 쪽이 실제로 수익을 냈는지 비교
  python research_cli.py --top 60 --compare

  # 결과를 JSON 으로 저장 (대시보드 '검증' 탭이 이 파일을 읽는다)
  python research_cli.py --top 100 --compare --out data/validation.json

네트워크가 막힌 환경에서는 --provider sample 로 동작만 확인할 수 있다
(합성 데이터라 결과 자체는 의미 없음).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from stocksystem.config import load_config
from stocksystem.data import get_provider
from stocksystem.data.universe import load_universe
from stocksystem.research import (SCORERS, bonferroni_t, compare_scorers,
                                  run_event_study)


def _progress(done: int, total: int, sym: str) -> None:
    bar = "█" * int(24 * done / total)
    sys.stderr.write(f"\r  [{bar:<24}] {done}/{total}  {sym:<8}")
    sys.stderr.flush()
    if done == total:
        sys.stderr.write("\n")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="점수 예측력 검증 (이벤트 스터디)",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--top", type=int, default=60,
                    help="시총 상위 N종목 (기본 60)")
    ap.add_argument("--symbols", nargs="*",
                    help="직접 지정 (--top 무시)")
    ap.add_argument("--period", default="5y",
                    help="분석 기간 (기본 5y, 'max' 도 가능)")
    ap.add_argument("--horizons", type=int, nargs="+", default=[20, 60],
                    help="예측 구간, 거래일 (기본 20 60)")
    ap.add_argument("--benchmark", default="SPY",
                    help="초과수익률 기준 (기본 SPY)")
    ap.add_argument("--score", default="종합기술점수(현행)",
                    choices=list(SCORERS), help="검증할 점수")
    ap.add_argument("--compare", action="store_true",
                    help="모든 점수를 비교 (추세 vs 역추세 판정)")
    ap.add_argument("--provider", help="데이터 소스 (yahoo/sample)")
    ap.add_argument("--out", help="결과 JSON 저장 경로")
    args = ap.parse_args()

    cfg = load_config()
    provider_name = args.provider or cfg.data_provider
    provider = get_provider(provider_name)

    if args.symbols:
        symbols = [s.upper() for s in args.symbols]
    else:
        symbols = [u.symbol for u in load_universe()][:args.top]

    targets = list(SCORERS) if args.compare else [args.score]

    print(f"데이터 소스 {provider_name} · 종목 {len(symbols)}개 · "
          f"기간 {args.period} · 벤치마크 {args.benchmark}", file=sys.stderr)
    if provider_name == "sample":
        print("⚠️  sample 은 합성 데이터입니다. 동작 확인용이며 결과에 "
              "의미가 없습니다.", file=sys.stderr)

    results = {}
    print(f"\n▶ 시세 수집 중 (점수 {len(targets)}종을 같은 시세로 평가)...",
          file=sys.stderr)
    try:
        if len(targets) > 1:
            # 시세를 한 번만 받아 모든 점수에 재사용한다
            results = compare_scorers(
                symbols, provider, cfg, horizons=tuple(args.horizons),
                period=args.period, benchmark=args.benchmark,
                progress=_progress)
        else:
            results = {targets[0]: run_event_study(
                symbols, provider, cfg, score_name=targets[0],
                horizons=tuple(args.horizons), period=args.period,
                benchmark=args.benchmark, progress=_progress)}
    except Exception as e:
        print(f"  실패: {e}", file=sys.stderr)
    for res in results.values():
        print(res.report())

    if not results:
        print("검증할 수 있는 결과가 없습니다. 네트워크 또는 종목을 확인하세요.",
              file=sys.stderr)
        return 1

    if len(results) > 1:
        print("\n" + "═" * 74)
        print(" 점수별 비교 — 어느 신호가 실제로 수익을 냈는가")
        print("═" * 74)
        h = max(args.horizons)
        # 점수 N종 × 구간 M개 = 가설 N*M 개를 동시에 검정하고 있다.
        n_tests = len(results) * len(args.horizons)
        t_crit = bonferroni_t(n_tests)
        print(f"{'점수':<22}{'IC':>10}{'t값':>9}{'롱숏':>11}"
              f"{'단조성':>9}{'유의':>7}{'보정후':>8}")
        print("─" * 82)
        for name, r in results.items():
            hr = r.horizons.get(h)
            if not hr:
                continue
            ic = "—" if hr.ic_mean != hr.ic_mean else f"{hr.ic_mean:+.4f}"
            t = "—" if hr.ic_t != hr.ic_t else f"{hr.ic_t:+.2f}"
            ls = ("—" if hr.long_short != hr.long_short
                  else f"{hr.long_short:+.2f}%p")
            mo = ("—" if hr.monotonicity != hr.monotonicity
                  else f"{hr.monotonicity:+.2f}")
            survives = (hr.ic_t == hr.ic_t and abs(hr.ic_t) >= t_crit)
            print(f"{name:<22}{ic:>10}{t:>9}{ls:>11}{mo:>9}"
                  f"{'✓' if hr.significant else '✗':>7}"
                  f"{'✓' if survives else '✗':>8}")
        print("─" * 82)
        print(f"(향후 {h}거래일 기준. IC=순위상관)")
        print(f"  유의   = 보정 없는 |t|>=2.00 — 단일 가설 기준")
        print(f"  보정후 = 다중검정 보정 |t|>={t_crit:.2f} "
              f"(가설 {n_tests}개, Bonferroni α=0.05)")
        print(f"  ※ 가설을 {n_tests}개 검정하면 그중 하나가 우연히 |t|>=2 를")
        print(f"     넘을 확률이 26%% 다. '보정후 ✓' 만 발견으로 취급하세요."
              .replace("%%", "%"))

    if args.out:
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(
                timespec="seconds"),
            "provider": provider_name,
            "period": args.period,
            "benchmark": args.benchmark,
            "n_symbols": len(symbols),
            "results": {k: v.to_dict() for k, v in results.items()},
        }
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        print(f"\n저장됨: {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
