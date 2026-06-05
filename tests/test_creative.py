"""크리에이티브 기능 4종 테스트: 팩터·몬테카를로·포트폴리오 닥터·공포탐욕."""
import numpy as np
import pandas as pd
import pytest

from stocksystem.config import load_config
from stocksystem.data import SampleProvider
from stocksystem.analysis import factors, montecarlo as mc, market as mk
from stocksystem.portfolio.analytics import analyze_portfolio


def _df(prices):
    idx = pd.bdate_range("2022-01-01", periods=len(prices))
    p = pd.Series(prices, index=idx, dtype=float)
    return pd.DataFrame({"Open": p, "High": p * 1.01, "Low": p * 0.99,
                         "Close": p, "Volume": 1_000_000})


# ---------- 팩터 레이더 ----------
def test_factor_profile_keys_and_range():
    p = factors.profile("AAPL", SampleProvider(), load_config())
    assert set(p.scores) == set(factors.FACTORS)
    assert all(0 <= v <= 100 for v in p.scores.values())
    assert 0 <= p.overall <= 100


def test_factor_compare_multiple():
    res = factors.compare(["AAPL", "MSFT", "NVDA"], SampleProvider(),
                          load_config())
    assert len(res) == 3
    assert all(r.name for r in res)


# ---------- 몬테카를로 / 타임머신 ----------
def test_past_investment_growth():
    df = _df(list(np.linspace(100, 200, 300)))   # 2배 상승
    r = mc.past_investment(df, 1000, df.index[0])
    assert r.current_value == pytest.approx(2000, rel=1e-6)
    assert r.total_return_pct == pytest.approx(100, rel=1e-6)


def test_simulate_structure_and_bounds():
    df = SampleProvider().price_history("AAPL", period="1y")
    sim = mc.simulate(df, horizon_days=60, n_sims=500, seed=1)
    assert list(sim.percentiles.columns) == ["p5", "p25", "p50", "p75", "p95"]
    assert len(sim.percentiles) == 60
    assert 0 <= sim.prob_profit <= 100
    # 백분위는 단조 증가 (p5 <= p50 <= p95)
    last = sim.percentiles.iloc[-1]
    assert last["p5"] <= last["p50"] <= last["p95"]


def test_simulate_target_probability():
    df = SampleProvider().price_history("MSFT", period="1y")
    s0 = float(df["Close"].iloc[-1])
    sim = mc.simulate(df, horizon_days=60, n_sims=500, target=s0 * 1.1, seed=2)
    assert sim.prob_target is not None
    assert 0 <= sim.prob_target <= 100


def test_simulate_deterministic_seed():
    df = SampleProvider().price_history("NVDA", period="1y")
    a = mc.simulate(df, 30, 300, seed=7).summary
    b = mc.simulate(df, 30, 300, seed=7).summary
    assert a == b


# ---------- 포트폴리오 닥터 ----------
def test_portfolio_weights_sum_100():
    rep = analyze_portfolio({"AAPL": 5000, "MSFT": 3000, "JNJ": 2000},
                            SampleProvider(), load_config())
    assert sum(rep.weights.values()) == pytest.approx(100, abs=0.5)
    assert 0 <= rep.diversification_score <= 100


def test_portfolio_concentration_flag():
    # 한 종목 90% → 집중 경고
    rep = analyze_portfolio({"AAPL": 9000, "MSFT": 1000},
                            SampleProvider(), load_config())
    assert rep.top_weight >= 80
    assert any("집중" in d for d in rep.diagnosis)


def test_portfolio_empty():
    rep = analyze_portfolio({}, SampleProvider(), load_config())
    assert rep.weights == {}


def test_portfolio_sector_breakdown():
    rep = analyze_portfolio({"AAPL": 5000, "JPM": 5000},
                            SampleProvider(), load_config())
    assert sum(rep.sector_weights.values()) == pytest.approx(100, abs=0.5)


# ---------- 공포·탐욕 지수 ----------
def test_fear_greed_range():
    fg = mk.fear_greed(SampleProvider(), load_config().technical)
    assert 0 <= fg.score <= 100
    assert fg.label
    assert len(fg.components) >= 1
    assert all(0 <= v <= 100 for v in fg.components.values())
