"""팩터(스타일) 프로파일 — 종목의 '투자 DNA' 를 5축으로 점수화.

가치 / 성장 / 수익성 / 모멘텀 / 안정성 을 각각 0~100 으로 환산해
레이더 차트로 종목을 비교할 수 있게 한다. 기존 펀더멘털 채점 함수를
재사용해 시스템 전체와 일관성을 유지한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..config import Config
from ..data.base import DataProvider
from . import fundamental as fa
from . import technical as ta

FACTORS = ["가치", "성장", "수익성", "모멘텀", "안정성"]


def _avg(*vals) -> float | None:
    xs = [v for v in vals if v is not None]
    return float(np.mean(xs)) if xs else None


def _momentum_score(df: pd.DataFrame) -> float | None:
    """최근 6개월(126거래일) 수익률을 0~100 으로."""
    close = df["Close"].dropna()
    if len(close) < 30:
        return None
    look = min(126, len(close) - 1)
    ret = close.iloc[-1] / close.iloc[-1 - look] - 1
    # -30% → 10점, 0% → 50점, +30% → 90점 (선형, 클립)
    return float(max(0, min(100, 50 + ret / 0.30 * 40)))


def _stability_score(df: pd.DataFrame, debt_score: float | None) -> float | None:
    """낮은 변동성 + 낮은 부채 = 높은 안정성."""
    close = df["Close"].dropna()
    parts = []
    if len(close) > 30:
        vol = close.pct_change().dropna().std() * np.sqrt(252)  # 연변동성
        # 0.15 → 85, 0.30 → 60, 0.50 → 35, 0.80 → 15
        vol_score = max(0, min(100, 100 - (vol - 0.10) / 0.70 * 85))
        parts.append(vol_score)
    if debt_score is not None:
        parts.append(debt_score)
    return float(np.mean(parts)) if parts else None


@dataclass
class FactorProfile:
    symbol: str
    name: str
    scores: dict[str, float] = field(default_factory=dict)  # 팩터→0~100
    overall: float = 0.0


def profile(symbol: str, provider: DataProvider, cfg: Config) -> FactorProfile:
    """한 종목의 5팩터 프로파일을 만든다."""
    name = symbol.upper()
    f = None
    df = None
    try:
        f = provider.fundamentals(symbol)
        name = f.name or symbol
    except Exception:
        pass
    try:
        df = provider.price_history(symbol, period="1y")
    except Exception:
        pass

    value = growth = quality = stability = None
    if f is not None:
        value = _avg(fa.score_pe(f.trailing_pe), fa.score_pb(f.price_to_book))
        growth = _avg(fa.score_growth(f.revenue_growth),
                      fa.score_growth(f.earnings_growth))
        quality = _avg(fa.score_roe(f.return_on_equity),
                       fa.score_margin(f.profit_margin))
        debt_score = fa.score_debt(f.debt_to_equity)
    else:
        debt_score = None

    momentum = None
    if df is not None and not df.empty:
        momentum = _avg(_momentum_score(df),
                        ta.analyze(df, cfg.technical).score)
    stability = _stability_score(df, debt_score) if df is not None else debt_score

    scores = {
        "가치": round(value, 1) if value is not None else 50.0,
        "성장": round(growth, 1) if growth is not None else 50.0,
        "수익성": round(quality, 1) if quality is not None else 50.0,
        "모멘텀": round(momentum, 1) if momentum is not None else 50.0,
        "안정성": round(stability, 1) if stability is not None else 50.0,
    }
    overall = round(float(np.mean(list(scores.values()))), 1)
    return FactorProfile(symbol=symbol.upper(), name=name,
                         scores=scores, overall=overall)


def compare(symbols: list[str], provider: DataProvider,
            cfg: Config) -> list[FactorProfile]:
    return [profile(s, provider, cfg) for s in symbols]
