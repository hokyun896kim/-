"""yfinance 기반 실시간 데이터 공급자.

로컬 PC 등 인터넷이 자유로운 환경에서 사용한다. Yahoo Finance 에서
무료로 시세와 재무 데이터를 가져온다. (API 키 불필요)

주의: 일부 클라우드/샌드박스 환경은 Yahoo 호스트를 차단할 수 있다.
그런 경우 SampleProvider 로 자동 대체하거나 config 에서 sample 을 쓴다.
"""
from __future__ import annotations

import pandas as pd

from .base import DataProvider, Fundamentals


class YahooProvider(DataProvider):
    def __init__(self):
        try:
            import yfinance  # noqa: F401
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                "yfinance 가 설치되어 있지 않습니다. `pip install yfinance` 후 사용하세요."
            ) from e

    def price_history(self, symbol: str, period: str = "1y",
                      interval: str = "1d") -> pd.DataFrame:
        import yfinance as yf

        df = yf.Ticker(symbol).history(period=period, interval=interval,
                                       auto_adjust=True)
        if df is None or df.empty:
            raise ValueError(f"'{symbol}' 시세를 가져오지 못했습니다.")
        return self._normalize(df)

    def fundamentals(self, symbol: str) -> Fundamentals:
        import yfinance as yf

        info = {}
        try:
            info = yf.Ticker(symbol).info or {}
        except Exception:
            info = {}

        def g(*keys):
            for k in keys:
                v = info.get(k)
                if v is not None:
                    return v
            return None

        return Fundamentals(
            symbol=symbol,
            name=g("shortName", "longName"),
            sector=g("sector"),
            market_cap=g("marketCap"),
            trailing_pe=g("trailingPE"),
            forward_pe=g("forwardPE"),
            price_to_book=g("priceToBook"),
            return_on_equity=g("returnOnEquity"),
            profit_margin=g("profitMargins"),
            revenue_growth=g("revenueGrowth"),
            earnings_growth=g("earningsGrowth", "earningsQuarterlyGrowth"),
            debt_to_equity=g("debtToEquity"),
            dividend_yield=g("dividendYield"),
            current_price=g("currentPrice", "regularMarketPrice"),
        )
