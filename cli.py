#!/usr/bin/env python3
"""터미널용 분석 CLI.

사용 예:
  python cli.py analyze AAPL MSFT          # 특정 종목 분석
  python cli.py watchlist                  # config.yaml 관심종목 전체
  python cli.py analyze NVDA --provider sample   # 오프라인 데모
"""
from __future__ import annotations

import argparse

from stocksystem.config import load_config
from stocksystem.data import get_provider
from stocksystem.analysis import analyze_symbol, analyze_watchlist


def _print_one(res) -> None:
    line = "─" * 60
    print(f"\n{line}")
    print(f" {res.symbol}  {res.name or ''}")
    print(line)
    price = res.technical.latest.get("close") if res.technical else None
    if price:
        print(f"  현재가      : ${price:,.2f}")
    print(f"  종합점수    : {res.total_score:>5.1f} / 100   →  "
          f"[{res.recommendation_label}]")
    if res.technical:
        print(f"  기술점수    : {res.technical.score:>5.1f}")
        sig = "  ".join(f"{k}:{v}" for k, v in res.technical.signals.items())
        print(f"    신호      : {sig}")
    if res.fundamental:
        print(f"  펀더멘털    : {res.fundamental.score:>5.1f}")
    if res.reasons:
        print("  판단 근거   :")
        for r in res.reasons:
            print(f"    • {r}")


def main() -> None:
    parser = argparse.ArgumentParser(description="미국주식 분석 CLI")
    parser.add_argument("command", choices=["analyze", "watchlist"])
    parser.add_argument("symbols", nargs="*", help="종목 티커 (analyze 시)")
    parser.add_argument("--provider", help="데이터 소스 (yahoo/sample)")
    parser.add_argument("--period", default="1y", help="조회 기간 (기본 1y)")
    args = parser.parse_args()

    cfg = load_config()
    provider_name = args.provider or cfg.data_provider
    provider = get_provider(provider_name)

    if args.command == "watchlist":
        symbols = cfg.watchlist
    else:
        symbols = [s.upper() for s in args.symbols] or cfg.watchlist

    print(f"데이터 소스: {provider_name} | 기간: {args.period} | "
          f"종목 {len(symbols)}개")

    if len(symbols) > 1:
        results = analyze_watchlist(symbols, provider, cfg, args.period)
        print(f"\n{'순위':>3} {'종목':<7}{'종합':>7}{'기술':>7}{'펀더':>7}  추천")
        print("─" * 50)
        for i, r in enumerate(results, 1):
            t = f"{r.technical.score:.1f}" if r.technical else "—"
            f = f"{r.fundamental.score:.1f}" if r.fundamental else "—"
            print(f"{i:>3} {r.symbol:<7}{r.total_score:>7.1f}{t:>7}{f:>7}  "
                  f"{r.recommendation_label}")
        print("\n--- 상세 ---")
        for r in results:
            _print_one(r)
    else:
        _print_one(analyze_symbol(symbols[0], provider, cfg, args.period))


if __name__ == "__main__":
    main()
