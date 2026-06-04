"""분석 대상 종목 유니버스.

미국 대형주(시가총액 상위) 목록을 번들 CSV(universe.csv)로 제공한다.
이 스냅샷을 기준으로 '시가총액 상위 N%' 필터, 섹터 필터를 적용한다.

실시간 모드에서도 유니버스 목록/시총 랭킹은 이 스냅샷을 쓰고(수백 종목을
매번 조회하면 느리므로), 개별 종목을 분석할 때 최신 재무를 받아온다.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import csv

CSV_PATH = Path(__file__).resolve().parent / "universe.csv"


@dataclass
class UniverseStock:
    symbol: str
    name: str
    sector: str
    market_cap_b: float        # 시가총액 (십억 달러, 스냅샷)


@lru_cache(maxsize=1)
def load_universe() -> list[UniverseStock]:
    """번들 CSV 를 읽어 시가총액 내림차순으로 반환."""
    rows: list[UniverseStock] = []
    with open(CSV_PATH, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                rows.append(UniverseStock(
                    symbol=r["symbol"].strip(),
                    name=r["name"].strip(),
                    sector=r["sector"].strip(),
                    market_cap_b=float(r["market_cap_b"]),
                ))
            except (KeyError, ValueError):
                continue
    rows.sort(key=lambda s: s.market_cap_b, reverse=True)
    return rows


def sectors() -> list[str]:
    """유니버스에 존재하는 섹터 목록 (정렬)."""
    return sorted({s.sector for s in load_universe()})


def market_cap_of(symbol: str) -> float | None:
    """스냅샷상 시가총액(십억 달러)."""
    sym = symbol.upper()
    for s in load_universe():
        if s.symbol == sym:
            return s.market_cap_b
    return None


def effective_cap(stock: UniverseStock,
                  live_caps: dict[str, float] | None) -> float:
    """랭킹에 쓸 시총(USD). 실시간 캐시가 있으면 우선, 없으면 스냅샷."""
    if live_caps:
        v = live_caps.get(stock.symbol)
        if v:
            return float(v)
    return stock.market_cap_b * 1e9


def filter_universe(top_pct: float = 50.0,
                    sector: str | None = None,
                    live_caps: dict[str, float] | None = None
                    ) -> list[UniverseStock]:
    """시가총액 상위 top_pct% 이내 + (선택) 섹터로 필터링.

    live_caps(심볼->USD)가 주어지면 그 실시간 시총으로 랭킹해 정확도를 높인다.
    없으면 번들 스냅샷 기준. top_pct=50 이면 상위 절반만 남긴다.
    """
    stocks = list(load_universe())
    if sector and sector != "전체":
        stocks = [s for s in stocks if s.sector == sector]
    # 실시간 캐시가 있으면 그 값으로 재정렬
    stocks.sort(key=lambda s: effective_cap(s, live_caps), reverse=True)
    if top_pct < 100:
        keep = max(1, int(len(stocks) * top_pct / 100))
        stocks = stocks[:keep]
    return stocks
