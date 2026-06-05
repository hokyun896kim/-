"""시장(지수) 분석 모듈 테스트."""
import numpy as np
import pandas as pd
import pytest

from stocksystem.config import TechnicalConfig
from stocksystem.data import SampleProvider
from stocksystem.analysis import market as mk


def _df(prices, vols=None):
    idx = pd.bdate_range("2021-01-01", periods=len(prices))
    p = pd.Series(prices, index=idx, dtype=float)
    v = pd.Series(vols if vols is not None else [1_000_000] * len(prices),
                  index=idx, dtype=float)
    return pd.DataFrame({"Open": p, "High": p * 1.01, "Low": p * 0.99,
                         "Close": p, "Volume": v})


def test_obv_accumulates_on_up_days():
    close = pd.Series([10, 11, 12, 11, 13], dtype=float)
    vol = pd.Series([100, 200, 300, 400, 500], dtype=float)
    o = mk.obv(close, vol)
    # 상승일 +, 하락일 -
    assert o.iloc[1] == 200          # up
    assert o.iloc[2] == 500          # up
    assert o.iloc[3] == 100          # down (500-400)
    assert o.iloc[4] == 600          # up


def test_atr_positive():
    df = _df(list(100 + np.cumsum(np.random.default_rng(0).normal(0, 1, 100))))
    a = mk.atr(df, 14).dropna()
    assert (a > 0).all()


def test_analyze_index_uptrend_bullish():
    # 꾸준한 상승 + 거래량 증가 → 강세 점수 높음
    n = 300
    prices = list(np.linspace(100, 200, n))
    vols = list(np.linspace(1e6, 3e6, n))
    res = mk.analyze_index(_df(prices, vols), TechnicalConfig(),
                           symbol="SPY", name="S&P 500")
    assert res.direction_score >= 60
    assert "상승" in res.trend
    assert len(res.narrative) >= 3
    assert res.key_levels["200일선"] is not None


def test_analyze_index_downtrend_bearish():
    n = 300
    prices = list(np.linspace(200, 100, n))
    res = mk.analyze_index(_df(prices), TechnicalConfig(),
                           symbol="QQQ", name="Nasdaq")
    assert res.direction_score <= 45
    assert "하락" in res.trend or "조정" in res.trend


def test_direction_score_in_range():
    df = SampleProvider().price_history("SPY", period="2y")
    res = mk.analyze_index(df, TechnicalConfig(), symbol="SPY", name="S&P 500")
    assert 0 <= res.direction_score <= 100
    assert res.direction_label
    for key in ["현재가", "50일선", "200일선", "52주 고점", "52주 저점"]:
        assert key in res.key_levels


def test_sub_scores_present():
    df = SampleProvider().price_history("^IXIC", period="2y")
    res = mk.analyze_index(df, TechnicalConfig(), symbol="^IXIC",
                           name="NASDAQ")
    assert "장기추세(200일선 위)" in res.sub_scores
    assert all(0 <= v <= 100 for v in res.sub_scores.values())
