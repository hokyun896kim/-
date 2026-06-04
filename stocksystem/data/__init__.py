"""데이터 계층: 공급자 선택 및 폴백 처리."""
from __future__ import annotations

from .base import (DataProvider, EarningsRow, Fundamentals, NewsItem,
                   UpcomingEvents)
from .sample import SampleProvider
from .yahoo import YahooProvider
from . import universe

__all__ = ["DataProvider", "Fundamentals", "NewsItem", "EarningsRow",
           "UpcomingEvents", "get_provider", "SampleProvider",
           "YahooProvider", "universe"]


def get_provider(name: str = "yahoo") -> DataProvider:
    """이름으로 데이터 공급자를 생성한다.

    - "yahoo": 실시간(yfinance). 설치/네트워크 문제 시 SampleProvider 로 폴백.
    - "sample": 오프라인 합성 데이터.
    """
    name = (name or "yahoo").lower()
    if name == "sample":
        return SampleProvider()
    try:
        return YahooProvider()
    except ImportError:
        return SampleProvider()
