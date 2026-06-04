"""데이터 공급자 공통 인터페이스.

모든 공급자는 동일한 형태의 데이터를 돌려줘야 한다:
- price_history(): OHLCV DataFrame (index=날짜, 컬럼: Open/High/Low/Close/Volume)
- fundamentals(): 재무 지표 dict (Fundamentals dataclass)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Optional

import pandas as pd

OHLCV_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


@dataclass
class Fundamentals:
    """종목의 기본적 분석용 재무 지표.

    값이 없으면 None. 분석 모듈은 None 을 안전하게 처리한다.
    """
    symbol: str
    name: Optional[str] = None
    sector: Optional[str] = None
    market_cap: Optional[float] = None
    trailing_pe: Optional[float] = None      # PER
    forward_pe: Optional[float] = None
    price_to_book: Optional[float] = None    # PBR
    return_on_equity: Optional[float] = None # ROE (소수, 0.25 = 25%)
    profit_margin: Optional[float] = None    # 순이익률 (소수)
    revenue_growth: Optional[float] = None   # 매출 성장률 (소수)
    earnings_growth: Optional[float] = None  # 이익 성장률 (소수)
    debt_to_equity: Optional[float] = None   # 부채비율 (%)
    dividend_yield: Optional[float] = None   # 배당수익률 (소수)
    current_price: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)


class DataProvider(ABC):
    """시세/재무 데이터 공급자 추상 클래스."""

    @abstractmethod
    def price_history(self, symbol: str, period: str = "1y",
                      interval: str = "1d") -> pd.DataFrame:
        """OHLCV 히스토리를 반환한다.

        반환 DataFrame 은 DatetimeIndex 와 OHLCV_COLUMNS 를 가져야 한다.
        """
        raise NotImplementedError

    @abstractmethod
    def fundamentals(self, symbol: str) -> Fundamentals:
        """재무 지표를 반환한다."""
        raise NotImplementedError

    # --- 공통 유틸 ---
    @staticmethod
    def _normalize(df: pd.DataFrame) -> pd.DataFrame:
        """OHLCV 컬럼만 추려 정렬/정리한다."""
        df = df.copy()
        # 컬럼명 표준화 (대소문자 차이 흡수)
        rename = {c: c.title() for c in df.columns}
        df = df.rename(columns=rename)
        keep = [c for c in OHLCV_COLUMNS if c in df.columns]
        df = df[keep].dropna(how="all")
        df = df[~df.index.duplicated(keep="last")].sort_index()
        return df
