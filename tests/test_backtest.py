"""백테스트 엔진 및 전략 테스트."""
import numpy as np
import pandas as pd
import pytest

from stocksystem.config import load_config, TechnicalConfig
from stocksystem.data import SampleProvider
from stocksystem.analysis import technical as ta
from stocksystem.backtest import run_backtest, backtest_symbol, STRATEGIES
from stocksystem.backtest.strategies import sma_crossover, score_threshold


def _trend_df(prices):
    idx = pd.bdate_range("2021-01-01", periods=len(prices))
    p = pd.Series(prices, index=idx, dtype=float)
    return pd.DataFrame({"Open": p, "High": p * 1.01, "Low": p * 0.99,
                         "Close": p, "Volume": 1_000_000})


def test_score_series_matches_analyze_last():
    # 벡터화 점수의 마지막 값이 analyze().score 와 일치해야 (일관성)
    df = SampleProvider().price_history("AAPL", period="1y")
    cfg = TechnicalConfig()
    ind = ta.compute_indicators(df, cfg)
    s = ta.score_series(ind, cfg)
    assert s.iloc[-1] == pytest.approx(ta.analyze(df, cfg).score, abs=0.05)


def test_full_long_equals_buy_and_hold_no_cost():
    df = _trend_df(list(np.linspace(100, 200, 120)))
    ind = ta.compute_indicators(df, TechnicalConfig())
    pos = pd.Series(1.0, index=ind.index)        # 항상 풀매수
    res = run_backtest(ind, pos, commission=0.0)
    # 수수료 0, 항상 보유 → 전략 == 단순보유
    assert res.equity.iloc[-1] == pytest.approx(res.benchmark.iloc[-1], rel=1e-6)


def test_cash_position_no_change():
    df = _trend_df(list(np.linspace(100, 200, 120)))
    ind = ta.compute_indicators(df, TechnicalConfig())
    pos = pd.Series(0.0, index=ind.index)        # 항상 현금
    res = run_backtest(ind, pos, initial_cash=10_000, commission=0.0)
    assert res.equity.iloc[-1] == pytest.approx(10_000)   # 변화 없음


def test_uptrend_sma_beats_cash():
    df = _trend_df(list(np.linspace(100, 250, 200)))
    ind = ta.compute_indicators(df, TechnicalConfig())
    pos = sma_crossover(ind, TechnicalConfig())
    res = run_backtest(ind, pos, commission=0.0)
    assert res.metrics["총수익률"] > 0
    assert res.metrics["시장노출"] > 0


def test_metrics_keys_present():
    res = backtest_symbol("MSFT", SampleProvider(), load_config(),
                          "종합 기술점수", period="2y")
    for k in ["총수익률", "단순보유수익률", "초과수익률", "최대낙폭(MDD)",
              "샤프지수", "승률", "거래횟수", "시장노출"]:
        assert k in res.metrics


def test_mdd_is_non_positive():
    res = backtest_symbol("NVDA", SampleProvider(), load_config(),
                          "골든크로스 (SMA 교차)", period="2y")
    assert res.metrics["최대낙폭(MDD)"] <= 0


def test_commission_reduces_return():
    df = SampleProvider().price_history("TSLA", period="2y")
    ind = ta.compute_indicators(df, TechnicalConfig())
    pos = score_threshold(ind, TechnicalConfig())
    no_fee = run_backtest(ind, pos, commission=0.0).equity.iloc[-1]
    with_fee = run_backtest(ind, pos, commission=0.005).equity.iloc[-1]
    assert with_fee <= no_fee


def test_trades_recorded():
    res = backtest_symbol("AAPL", SampleProvider(), load_config(),
                          "골든크로스 (SMA 교차)", period="5y")
    assert res.metrics["거래횟수"] == len(res.trades)
    # 완료된 거래는 진입/청산가가 있어야
    for t in res.trades:
        assert t.entry_price > 0


def test_all_strategies_run():
    cfg = load_config()
    prov = SampleProvider()
    for name in STRATEGIES:
        res = backtest_symbol("GOOGL", prov, cfg, name, period="2y")
        assert "총수익률" in res.metrics
        assert len(res.equity) > 0


def test_no_lookahead_first_day_flat():
    # shift(1) 때문에 첫날은 항상 노출 0 → 첫날 수익 변화 없음
    df = _trend_df(list(np.linspace(100, 200, 120)))
    ind = ta.compute_indicators(df, TechnicalConfig())
    pos = pd.Series(1.0, index=ind.index)
    res = run_backtest(ind, pos, initial_cash=10_000, commission=0.0)
    assert res.equity.iloc[0] == pytest.approx(10_000)
