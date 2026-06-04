"""오프라인 샘플 데이터 공급자.

인터넷이 없거나 차단된 환경(예: 일부 클라우드 샌드박스)에서도 시스템 전체를
실행/시연/테스트할 수 있도록 결정론적(deterministic) 합성 데이터를 생성한다.

- 시드를 심볼에서 만들어 같은 심볼은 항상 같은 데이터를 돌려준다.
- 기하 브라운 운동(GBM) 비슷한 방식으로 현실적인 가격 곡선을 만든다.
"""
from __future__ import annotations

import hashlib
from datetime import timedelta

import numpy as np
import pandas as pd

from .base import (DataProvider, EarningsRow, Fundamentals, NewsItem,
                   UpcomingEvents)

# 데모용 종목 메타데이터 (실제와 무관한 합성 값)
_META = {
    "AAPL": ("Apple Inc.", "Technology", 190.0, 0.20),
    "MSFT": ("Microsoft Corp.", "Technology", 420.0, 0.18),
    "NVDA": ("NVIDIA Corp.", "Technology", 120.0, 0.45),
    "GOOGL": ("Alphabet Inc.", "Communication Services", 175.0, 0.22),
    "AMZN": ("Amazon.com Inc.", "Consumer Cyclical", 185.0, 0.28),
    "META": ("Meta Platforms Inc.", "Communication Services", 500.0, 0.30),
    "TSLA": ("Tesla Inc.", "Consumer Cyclical", 250.0, 0.50),
    "JPM": ("JPMorgan Chase & Co.", "Financial Services", 200.0, 0.16),
    "V": ("Visa Inc.", "Financial Services", 280.0, 0.15),
    "JNJ": ("Johnson & Johnson", "Healthcare", 150.0, 0.12),
}


def _seed(symbol: str) -> int:
    return int(hashlib.md5(symbol.upper().encode()).hexdigest(), 16) % (2**32)


def _period_to_days(period: str) -> int:
    table = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365,
             "2y": 730, "5y": 1825, "max": 1825}
    return table.get(period, 365)


class SampleProvider(DataProvider):
    def price_history(self, symbol: str, period: str = "1y",
                      interval: str = "1d") -> pd.DataFrame:
        rng = np.random.default_rng(_seed(symbol))
        _, _, base_price, annual_vol = _META.get(
            symbol.upper(), ("Sample Co.", "Unknown", 100.0, 0.25))

        days = _period_to_days(period)
        # 영업일 기준 인덱스 생성
        idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=days)
        n = len(idx)

        daily_vol = annual_vol / np.sqrt(252)
        drift = 0.08 / 252  # 연 8% 추세 가정
        shocks = rng.normal(drift, daily_vol, n)
        # 약한 추세 사이클을 더해 지표가 의미있게 움직이도록 함
        cycle = 0.0015 * np.sin(np.linspace(0, 6 * np.pi, n))
        returns = shocks + cycle

        close = base_price * np.exp(np.cumsum(returns))
        # OHLCV 구성
        intraday = np.abs(rng.normal(0, daily_vol, n)) * close
        open_ = close * (1 + rng.normal(0, daily_vol * 0.3, n))
        high = np.maximum(open_, close) + intraday
        low = np.minimum(open_, close) - intraday
        volume = rng.integers(5_000_000, 60_000_000, n)

        df = pd.DataFrame(
            {"Open": open_, "High": high, "Low": low,
             "Close": close, "Volume": volume},
            index=idx,
        )
        return self._normalize(df)

    def fundamentals(self, symbol: str) -> Fundamentals:
        rng = np.random.default_rng(_seed(symbol) + 1)
        name, sector, price, vol = _META.get(
            symbol.upper(), ("Sample Co.", "Unknown", 100.0, 0.25))

        # 유니버스 스냅샷에 있으면 이름/섹터/시총을 맞춰 일관성 유지
        mcap = None
        try:
            from .universe import load_universe
            for u in load_universe():
                if u.symbol == symbol.upper():
                    name, sector = u.name, u.sector
                    mcap = u.market_cap_b * 1e9
                    break
        except Exception:
            pass
        if mcap is None:
            mcap = float(price * rng.integers(1_000, 16_000) * 1e6)

        return Fundamentals(
            symbol=symbol.upper(),
            name=name,
            sector=sector,
            market_cap=mcap,
            trailing_pe=round(float(rng.uniform(12, 45)), 1),
            forward_pe=round(float(rng.uniform(10, 38)), 1),
            price_to_book=round(float(rng.uniform(2, 18)), 1),
            return_on_equity=round(float(rng.uniform(0.05, 0.5)), 3),
            profit_margin=round(float(rng.uniform(0.05, 0.35)), 3),
            revenue_growth=round(float(rng.uniform(-0.05, 0.4)), 3),
            earnings_growth=round(float(rng.uniform(-0.1, 0.5)), 3),
            debt_to_equity=round(float(rng.uniform(20, 180)), 1),
            dividend_yield=round(float(rng.uniform(0, 0.03)), 4),
            current_price=round(float(price), 2),
        )

    def news(self, symbol: str, limit: int = 8) -> list[NewsItem]:
        rng = np.random.default_rng(_seed(symbol) + 2)
        name = _META.get(symbol.upper(), ("Sample Co.",))[0]
        templates = [
            (f"{name} beats quarterly earnings estimates on strong demand", 1),
            (f"Analysts upgrade {symbol.upper()} citing robust growth momentum", 1),
            (f"{name} announces new product, shares rally", 1),
            (f"{name} raises full-year guidance after record revenue", 1),
            (f"{name} stock jumps as profit tops forecasts", 1),
            (f"{name} faces lawsuit over alleged practices, shares fall", -1),
            (f"Analysts downgrade {symbol.upper()} on margin pressure concerns", -1),
            (f"{name} misses revenue estimates, guidance disappoints", -1),
            (f"Regulatory probe weighs on {name} outlook", -1),
            (f"{name} holds steady as market awaits earnings", 0),
            (f"{name} in focus ahead of upcoming product event", 0),
        ]
        publishers = ["Reuters", "Bloomberg", "CNBC", "MarketWatch",
                      "Yahoo Finance", "Barron's"]
        idx = rng.permutation(len(templates))[:limit]
        today = pd.Timestamp.today().normalize()
        items: list[NewsItem] = []
        for i, j in enumerate(idx):
            title = templates[j][0]
            items.append(NewsItem(
                title=title,
                publisher=str(rng.choice(publishers)),
                link="https://finance.example.com/news",
                published=(today - timedelta(days=int(i))).strftime("%Y-%m-%d"),
                summary=None,
            ))
        return items

    def earnings_history(self, symbol: str, limit: int = 4) -> list[EarningsRow]:
        rng = np.random.default_rng(_seed(symbol) + 3)
        rows: list[EarningsRow] = []
        base_eps = float(rng.uniform(0.8, 3.5))
        base_rev = float(rng.uniform(5, 90)) * 1e9
        today = pd.Timestamp.today().normalize()
        for q in range(limit, 0, -1):
            est = round(base_eps * (1 + 0.03 * (limit - q)), 2)
            actual = round(est * (1 + float(rng.uniform(-0.08, 0.12))), 2)
            rev = round(base_rev * (1 + 0.02 * (limit - q)), 0)
            date = today - timedelta(days=90 * q)
            rows.append(EarningsRow(period=date.strftime("%Y-%m-%d"),
                                    eps_estimate=est, eps_actual=actual,
                                    revenue=rev))
        return rows

    def events(self, symbol: str) -> UpcomingEvents:
        rng = np.random.default_rng(_seed(symbol) + 4)
        today = pd.Timestamp.today().normalize()
        next_earn = today + timedelta(days=int(rng.integers(5, 60)))
        has_div = bool(rng.random() > 0.4)
        ev = UpcomingEvents(
            symbol=symbol.upper(),
            next_earnings_date=next_earn.strftime("%Y-%m-%d"),
        )
        if has_div:
            ev.ex_dividend_date = (today + timedelta(
                days=int(rng.integers(3, 45)))).strftime("%Y-%m-%d")
            ev.dividend_amount = round(float(rng.uniform(0.2, 1.2)), 2)
        return ev
