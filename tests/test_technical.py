"""기술적 분석 지표/신호 테스트."""
import numpy as np
import pandas as pd
import pytest

from stocksystem.config import TechnicalConfig
from stocksystem.analysis import technical as ta


def _make_df(prices):
    idx = pd.bdate_range("2023-01-01", periods=len(prices))
    p = pd.Series(prices, index=idx, dtype=float)
    return pd.DataFrame({
        "Open": p, "High": p * 1.01, "Low": p * 0.99,
        "Close": p, "Volume": np.full(len(prices), 1_000_000),
    })


def test_sma_basic():
    s = pd.Series([1, 2, 3, 4, 5], dtype=float)
    out = ta.sma(s, 3)
    assert np.isnan(out.iloc[1])           # 기간 미충족 → NaN
    assert out.iloc[2] == pytest.approx(2.0)
    assert out.iloc[4] == pytest.approx(4.0)


def test_rsi_all_gains_is_100():
    s = pd.Series(np.arange(1, 40, dtype=float))   # 계속 상승
    r = ta.rsi(s, 14).dropna()
    assert r.iloc[-1] == pytest.approx(100.0)


def test_rsi_all_losses_near_zero():
    s = pd.Series(np.arange(40, 1, -1, dtype=float))  # 계속 하락
    r = ta.rsi(s, 14).dropna()
    assert r.iloc[-1] < 5.0


def test_rsi_bounds():
    rng = np.random.default_rng(0)
    s = pd.Series(100 + np.cumsum(rng.normal(0, 1, 200)))
    r = ta.rsi(s, 14).dropna()
    assert (r >= 0).all() and (r <= 100).all()


def test_macd_columns():
    s = pd.Series(100 + np.cumsum(np.random.default_rng(1).normal(0, 1, 100)))
    m = ta.macd(s)
    assert list(m.columns) == ["macd", "signal", "hist"]
    # 히스토그램 = macd - signal
    assert (m["hist"] - (m["macd"] - m["signal"])).abs().max() < 1e-9


def test_bollinger_pct_b():
    s = pd.Series(100 + np.cumsum(np.random.default_rng(2).normal(0, 1, 100)))
    b = ta.bollinger(s, 20, 2.0)
    # 중심선은 상/하단 사이
    valid = b.dropna()
    assert (valid["bb_lower"] <= valid["bb_mid"]).all()
    assert (valid["bb_mid"] <= valid["bb_upper"]).all()


def test_uptrend_scores_bullish():
    # 꾸준한 상승 추세 → 점수가 중립(50) 이상이어야
    df = _make_df(list(np.linspace(100, 200, 120)))
    res = ta.analyze(df, TechnicalConfig(), symbol="UP")
    assert res.score >= 50
    assert res.signals["추세(SMA교차)"] == "buy"


def test_downtrend_scores_bearish():
    df = _make_df(list(np.linspace(200, 100, 120)))
    res = ta.analyze(df, TechnicalConfig(), symbol="DOWN")
    assert res.score <= 50
    assert res.signals["추세(SMA교차)"] == "sell"


def test_score_range():
    df = _make_df(list(100 + np.cumsum(
        np.random.default_rng(3).normal(0, 2, 200))))
    res = ta.analyze(df, TechnicalConfig(), symbol="RND")
    assert 0 <= res.score <= 100
