"""오프라인 샘플 데이터 공급자.

인터넷이 없거나 차단된 환경(예: 일부 클라우드 샌드박스)에서도 시스템 전체를
실행/시연/테스트할 수 있도록 결정론적(deterministic) 합성 데이터를 생성한다.

- 시드를 심볼에서 만들어 같은 심볼은 항상 같은 데이터를 돌려준다.
- 기하 브라운 운동(GBM) 비슷한 방식으로 현실적인 가격 곡선을 만든다.
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from .base import DataProvider, Fundamentals

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

        return Fundamentals(
            symbol=symbol.upper(),
            name=name,
            sector=sector,
            market_cap=float(price * rng.integers(1_000, 16_000) * 1e6),
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
