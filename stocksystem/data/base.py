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


@dataclass
class NewsItem:
    """뉴스 헤드라인 한 건."""
    title: str
    publisher: Optional[str] = None
    link: Optional[str] = None
    published: Optional[str] = None      # ISO 날짜 문자열
    summary: Optional[str] = None
    sentiment: Optional[float] = None    # -1(부정) ~ +1(긍정), 분석 후 채워짐


@dataclass
class EarningsRow:
    """분기 실적 한 줄."""
    period: str                          # 예: "2025Q2"
    eps_estimate: Optional[float] = None # 시장 예상 EPS
    eps_actual: Optional[float] = None   # 실제 발표 EPS
    revenue: Optional[float] = None      # 매출 (USD)

    @property
    def surprise_pct(self) -> Optional[float]:
        """EPS 서프라이즈(%) = (실제-예상)/|예상|."""
        if self.eps_actual is None or self.eps_estimate in (None, 0):
            return None
        return (self.eps_actual - self.eps_estimate) / abs(self.eps_estimate) * 100


@dataclass
class UpcomingEvents:
    """다가오는 일정."""
    symbol: str
    next_earnings_date: Optional[str] = None    # 다음 실적발표 예정일
    ex_dividend_date: Optional[str] = None       # 배당락일
    dividend_amount: Optional[float] = None      # 주당 배당금
    last_split_date: Optional[str] = None
    notes: list[str] = None

    def __post_init__(self):
        if self.notes is None:
            self.notes = []


@dataclass
class Financials:
    """손익계산서 시계열 (헤게모니 스프레드 계산용).

    각 Series 는 날짜 오름차순(과거→최신) 인덱스, 값은 USD.
    """
    symbol: str
    annual_revenue: "pd.Series | None" = None
    annual_op_income: "pd.Series | None" = None
    quarterly_revenue: "pd.Series | None" = None
    quarterly_op_income: "pd.Series | None" = None


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

    # --- 선택 기능 (기본은 빈 값; 공급자별로 재정의) ---
    def market_cap(self, symbol: str) -> float | None:
        """현재 시가총액(USD). 기본은 fundamentals 에서 가져온다.

        공급자가 더 빠른 경로(예: fast_info)를 제공하면 재정의한다.
        """
        try:
            return self.fundamentals(symbol).market_cap
        except Exception:
            return None

    def news(self, symbol: str, limit: int = 8) -> list["NewsItem"]:
        """최근 뉴스 헤드라인 목록."""
        return []

    def earnings_history(self, symbol: str, limit: int = 4) -> list["EarningsRow"]:
        """최근 분기 실적 (오래된→최신)."""
        return []

    def events(self, symbol: str) -> "UpcomingEvents":
        """다가오는 일정(실적/배당)."""
        return UpcomingEvents(symbol=symbol.upper())

    def income_statement(self, symbol: str) -> "Financials":
        """연간·분기 손익계산서(매출/영업이익)를 반환한다."""
        return Financials(symbol=symbol.upper())

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
