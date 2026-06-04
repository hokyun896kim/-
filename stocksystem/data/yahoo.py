"""yfinance 기반 실시간 데이터 공급자.

로컬 PC 등 인터넷이 자유로운 환경에서 사용한다. Yahoo Finance 에서
무료로 시세와 재무 데이터를 가져온다. (API 키 불필요)

주의: 일부 클라우드/샌드박스 환경은 Yahoo 호스트를 차단할 수 있다.
그런 경우 SampleProvider 로 자동 대체하거나 config 에서 sample 을 쓴다.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from .base import (DataProvider, EarningsRow, Fundamentals, NewsItem,
                   UpcomingEvents)


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

    def market_cap(self, symbol: str) -> float | None:
        import yfinance as yf

        t = yf.Ticker(symbol)
        # fast_info 는 .info 보다 가벼워 다수 종목 조회에 적합
        try:
            mc = t.fast_info.get("market_cap") if hasattr(t.fast_info, "get") \
                else t.fast_info["market_cap"]
            if mc:
                return float(mc)
        except Exception:
            pass
        try:
            return float((t.info or {}).get("marketCap"))
        except (TypeError, ValueError, Exception):
            return None

    def news(self, symbol: str, limit: int = 8) -> list[NewsItem]:
        import yfinance as yf

        items: list[NewsItem] = []
        try:
            raw = yf.Ticker(symbol).news or []
        except Exception:
            raw = []

        for n in raw[:limit]:
            # yfinance 버전에 따라 평면형 또는 {'content': {...}} 형태
            content = n.get("content", n) if isinstance(n, dict) else {}
            title = content.get("title") or n.get("title")
            if not title:
                continue
            pub = (content.get("provider", {}) or {}).get("displayName") \
                or n.get("publisher")
            link = n.get("link")
            if not link:
                link = (content.get("canonicalUrl", {}) or {}).get("url")
            published = content.get("pubDate") or _epoch_to_iso(
                n.get("providerPublishTime"))
            summary = content.get("summary") or content.get("description")
            items.append(NewsItem(title=title, publisher=pub, link=link,
                                  published=published, summary=summary))
        return items

    def earnings_history(self, symbol: str, limit: int = 4) -> list[EarningsRow]:
        import yfinance as yf

        rows: list[EarningsRow] = []
        try:
            df = yf.Ticker(symbol).get_earnings_dates(limit=limit * 3)
        except Exception:
            df = None
        if df is None or df.empty:
            return rows

        # 이미 실적이 발표된(=과거) 행만, 최신 limit개
        now = pd.Timestamp.now(tz=df.index.tz) if df.index.tz else pd.Timestamp.now()
        past = df[df.index <= now].head(limit)
        for ts, r in past.iloc[::-1].iterrows():     # 오래된→최신
            rows.append(EarningsRow(
                period=ts.strftime("%Y-%m-%d"),
                eps_estimate=_num(r.get("EPS Estimate")),
                eps_actual=_num(r.get("Reported EPS")),
            ))
        return rows

    def events(self, symbol: str) -> UpcomingEvents:
        import yfinance as yf

        ev = UpcomingEvents(symbol=symbol.upper())
        t = yf.Ticker(symbol)
        try:
            cal = t.calendar or {}
        except Exception:
            cal = {}
        if isinstance(cal, dict):
            ed = cal.get("Earnings Date")
            if isinstance(ed, (list, tuple)) and ed:
                ev.next_earnings_date = str(ed[0])
            elif ed:
                ev.next_earnings_date = str(ed)
            exd = cal.get("Ex-Dividend Date")
            if exd:
                ev.ex_dividend_date = str(exd)
        try:
            info = t.info or {}
            ev.dividend_amount = info.get("dividendRate")
        except Exception:
            pass
        return ev


def _epoch_to_iso(ts) -> str | None:
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")
    except (ValueError, OSError, TypeError):
        return None


def _num(v):
    try:
        if v is None or pd.isna(v):
            return None
        return float(v)
    except (TypeError, ValueError):
        return None
