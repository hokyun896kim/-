"""몬테카를로 시뮬레이터 & 과거 투자 계산기 ('타임머신').

- past_investment(): 과거에 투자했다면 지금 얼마? (실제 가격 경로 기반)
- simulate(): 과거 수익률 통계로 미래 주가를 수천 번 시뮬레이션 →
  확률 구간(부채꼴)과 목표가 도달 확률을 계산.

기하 브라운 운동(GBM)을 일별 로그수익률의 평균·표준편차로 추정해 사용한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

TRADING_DAYS = 252


@dataclass
class PastResult:
    symbol: str
    start_date: str
    end_date: str
    invested: float
    current_value: float
    total_return_pct: float
    cagr_pct: float
    equity: pd.Series          # 투자금 가치 추이


def past_investment(df: pd.DataFrame, amount: float,
                    start: str | pd.Timestamp) -> PastResult:
    """start 시점에 amount(USD)를 넣었다면 지금 가치는?"""
    close = df["Close"].dropna()
    start = pd.Timestamp(start)
    if close.index.tz is not None and start.tzinfo is None:
        start = start.tz_localize(close.index.tz)
    sub = close[close.index >= start]
    if sub.empty:
        sub = close
    shares = amount / float(sub.iloc[0])
    equity = shares * sub
    cur = float(equity.iloc[-1])
    total = cur / amount - 1
    years = max((sub.index[-1] - sub.index[0]).days / 365.25, 1e-9)
    cagr = (cur / amount) ** (1 / years) - 1
    return PastResult(
        symbol="", start_date=str(sub.index[0].date()),
        end_date=str(sub.index[-1].date()), invested=round(amount, 2),
        current_value=round(cur, 2), total_return_pct=round(total * 100, 2),
        cagr_pct=round(cagr * 100, 2), equity=equity)


@dataclass
class SimResult:
    symbol: str
    start_price: float
    horizon_days: int
    n_sims: int
    percentiles: pd.DataFrame      # 컬럼 p5,p25,p50,p75,p95 / index=일자
    final_prices: np.ndarray       # 시뮬 종료 시 가격 분포
    prob_profit: float             # 시작가 대비 상승 확률 %
    prob_target: float | None      # 목표가 도달 확률 % (목표 주어진 경우)
    target: float | None = None
    summary: dict = field(default_factory=dict)


def simulate(df: pd.DataFrame, horizon_days: int = 126, n_sims: int = 2000,
             target: float | None = None, seed: int = 42) -> SimResult:
    """과거 일별 로그수익률 통계로 미래 주가 경로를 시뮬레이션한다."""
    close = df["Close"].dropna()
    log_ret = np.log(close / close.shift(1)).dropna()
    mu, sigma = float(log_ret.mean()), float(log_ret.std())
    s0 = float(close.iloc[-1])

    rng = np.random.default_rng(seed)
    # (n_sims, horizon) 일별 로그수익률 → 누적 → 가격 경로
    shocks = rng.normal(mu, sigma, size=(n_sims, horizon_days))
    paths = s0 * np.exp(np.cumsum(shocks, axis=1))

    qs = [5, 25, 50, 75, 95]
    pct = np.percentile(paths, qs, axis=0)            # (5, horizon)
    future_idx = pd.bdate_range(close.index[-1] + pd.Timedelta(days=1),
                                periods=horizon_days)
    perc_df = pd.DataFrame(pct.T, index=future_idx,
                           columns=[f"p{q}" for q in qs])

    finals = paths[:, -1]
    prob_profit = float((finals > s0).mean() * 100)
    prob_target = (float((finals >= target).mean() * 100)
                   if target else None)

    summary = {
        "현재가": round(s0, 2),
        "중앙 예상(p50)": round(float(np.median(finals)), 2),
        "낙관(p95)": round(float(np.percentile(finals, 95)), 2),
        "비관(p5)": round(float(np.percentile(finals, 5)), 2),
        "기대수익률(중앙)": round((np.median(finals) / s0 - 1) * 100, 1),
    }
    return SimResult(
        symbol="", start_price=round(s0, 2), horizon_days=horizon_days,
        n_sims=n_sims, percentiles=perc_df, final_prices=finals,
        prob_profit=round(prob_profit, 1), prob_target=(
            round(prob_target, 1) if prob_target is not None else None),
        target=target, summary=summary)
