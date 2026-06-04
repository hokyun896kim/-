"""백테스트 실행 엔진.

'목표 포지션' 시계열(0=현금, 1=풀매수)을 받아 일별 자산곡선을 만들고,
성과 지표를 계산한다. 단순 보유(Buy&Hold)와 비교한다.

룩어헤드 편향 방지: 오늘 종가로 계산한 신호는 '다음 날' 수익률부터 반영한다
(position.shift(1)). 매매가 일어나는 날엔 수수료를 차감한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

TRADING_DAYS = 252


@dataclass
class Trade:
    entry_date: str
    exit_date: str | None
    entry_price: float
    exit_price: float | None
    return_pct: float | None        # 수수료 반영 (소수)


@dataclass
class BacktestResult:
    symbol: str
    strategy: str
    equity: pd.Series               # 전략 자산곡선
    benchmark: pd.Series            # 단순 보유 자산곡선
    position: pd.Series             # 적용된 포지션 (0/1)
    trades: list[Trade] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)


def _max_drawdown(equity: pd.Series) -> float:
    """최대 낙폭(MDD, 음수 소수). -0.25 = -25%."""
    roll_max = equity.cummax()
    dd = equity / roll_max - 1.0
    return float(dd.min()) if len(dd) else 0.0


def _sharpe(daily_returns: pd.Series) -> float:
    """연율화 샤프지수 (무위험수익률 0 가정)."""
    r = daily_returns.dropna()
    if len(r) < 2 or r.std() == 0:
        return 0.0
    return float(r.mean() / r.std() * np.sqrt(TRADING_DAYS))


def _extract_trades(position: pd.Series, close: pd.Series,
                    commission: float) -> list[Trade]:
    """포지션 0→1(진입), 1→0(청산) 시점으로 라운드트립 거래를 복원한다."""
    trades: list[Trade] = []
    entry_price = None
    entry_date = None
    prev = 0.0
    for ts, p in position.items():
        if prev <= 0 and p > 0:                 # 진입
            entry_price = float(close.loc[ts])
            entry_date = ts
        elif prev > 0 and p <= 0 and entry_price:  # 청산
            exit_price = float(close.loc[ts])
            ret = exit_price / entry_price - 1.0 - 2 * commission
            trades.append(Trade(str(entry_date.date()), str(ts.date()),
                                entry_price, exit_price, ret))
            entry_price = entry_date = None
        prev = p
    # 청산되지 않고 보유 중인 포지션
    if entry_price is not None:
        last_ts = position.index[-1]
        exit_price = float(close.loc[last_ts])
        ret = exit_price / entry_price - 1.0 - commission
        trades.append(Trade(str(entry_date.date()), None,
                            entry_price, exit_price, ret))
    return trades


def run_backtest(ind: pd.DataFrame, position: pd.Series, *,
                 symbol: str = "", strategy: str = "",
                 initial_cash: float = 10_000.0,
                 commission: float = 0.001) -> BacktestResult:
    """포지션 시계열로 백테스트를 수행한다.

    ind: 'Close' 컬럼을 포함한 (지표가 계산된) 가격 DataFrame
    position: ind.index 에 정렬된 0/1 목표 포지션
    commission: 거래대금 대비 수수료율 (편도, 예: 0.001 = 0.1%)
    """
    close = ind["Close"].astype(float)
    pos = position.reindex(close.index).ffill().fillna(0.0).clip(0, 1)

    ret = close.pct_change().fillna(0.0)
    # 오늘 신호는 다음 날부터 반영 (룩어헤드 방지)
    applied = pos.shift(1).fillna(0.0)
    gross = applied * ret
    # 포지션이 바뀌는 날 수수료 차감
    turnover = pos.diff().abs().fillna(pos.abs())
    cost = turnover * commission
    net = gross - cost

    equity = initial_cash * (1 + net).cumprod()
    benchmark = initial_cash * (close / close.iloc[0])

    trades = _extract_trades(pos, close, commission)
    wins = [t for t in trades if t.return_pct is not None and t.return_pct > 0]

    years = max(len(close) / TRADING_DAYS, 1e-9)
    total_return = float(equity.iloc[-1] / initial_cash - 1.0)
    bench_return = float(benchmark.iloc[-1] / initial_cash - 1.0)
    cagr = float((equity.iloc[-1] / initial_cash) ** (1 / years) - 1.0)

    metrics = {
        "총수익률": round(total_return * 100, 2),
        "단순보유수익률": round(bench_return * 100, 2),
        "초과수익률": round((total_return - bench_return) * 100, 2),
        "연복리수익률(CAGR)": round(cagr * 100, 2),
        "최대낙폭(MDD)": round(_max_drawdown(equity) * 100, 2),
        "단순보유MDD": round(_max_drawdown(benchmark) * 100, 2),
        "샤프지수": round(_sharpe(net), 2),
        "연변동성": round(float(net.std() * np.sqrt(TRADING_DAYS) * 100), 2),
        "거래횟수": len(trades),
        "승률": round(len(wins) / len(trades) * 100, 1) if trades else 0.0,
        "시장노출": round(float(applied.mean()) * 100, 1),
        "최종자산": round(float(equity.iloc[-1]), 2),
    }
    return BacktestResult(symbol=symbol, strategy=strategy, equity=equity,
                          benchmark=benchmark, position=pos,
                          trades=trades, metrics=metrics)
