"""선취매 레이더 테스트."""
import numpy as np
import pandas as pd
import pytest

from stocksystem.config import load_config, TechnicalConfig
from stocksystem.data import SampleProvider
from stocksystem.analysis import earlybird as eb


def _df(closes, vols=None):
    idx = pd.bdate_range("2023-01-01", periods=len(closes))
    c = pd.Series(closes, index=idx, dtype=float)
    v = pd.Series(vols if vols is not None else [1e6] * len(closes),
                  index=idx, dtype=float)
    return pd.DataFrame({"Open": c, "High": c * 1.01, "Low": c * 0.99,
                         "Close": c, "Volume": v})


def test_extended_stock_low_score():
    # 급등 + 신고가 = 이미 늦음 → 낮은 점수, extended 플래그
    closes = list(np.linspace(100, 180, 260))  # 끝까지 신고가
    res = eb.analyze(_df(closes), TechnicalConfig(), symbol="HOT")
    assert res.extended is True
    assert res.score < 50
    assert "과열" in res.stage or "후반" in res.stage


def test_quiet_accumulation_detected():
    # 상승 → 고점 → 눌림(-12%) → 조용히 천천히 매집(거래량 늘며 주가 완만 상승)
    base = list(np.linspace(100, 160, 150))      # 상승 후 고점 160
    pull = list(np.linspace(160, 140, 30))       # 눌림
    accum = list(np.linspace(140, 147, 80))      # 완만한 재매집(횡보성)
    closes = base + pull + accum
    vols = [1e6] * 180 + list(np.linspace(1e6, 3e6, 80))  # 매집 구간 거래량 증가
    res = eb.analyze(_df(closes, vols), TechnicalConfig(), symbol="ACC")
    assert res.accumulation is True            # OBV↑ + 주가 횡보 = 조용한 매집
    assert any("매집" in r for r in res.reasons)


def test_score_bounds_and_stage():
    df = SampleProvider().price_history("AAPL", period="1y")
    res = eb.analyze(df, TechnicalConfig(), symbol="AAPL")
    assert 0 <= res.score <= 100
    assert res.stage
    for k in ["현재가", "RSI", "3개월수익", "52주고점比"]:
        assert k in res.metrics


def test_downtrend_penalized():
    closes = list(np.linspace(200, 120, 260))    # 지속 하락
    res = eb.analyze(_df(closes), TechnicalConfig(), symbol="DOWN")
    assert "추세이탈" in res.stage or res.score < 45


def test_pe_affects_score():
    df = _df(list(np.linspace(100, 130, 200)))
    cheap = eb.analyze(df, TechnicalConfig(), symbol="X", pe=15)
    rich = eb.analyze(df, TechnicalConfig(), symbol="X", pe=80)
    assert cheap.score >= rich.score


def test_rank_sorted_and_integration():
    cfg = load_config()
    res = eb.rank(["AAPL", "MSFT", "NVDA", "JPM"], SampleProvider(), cfg)
    scores = [r.score for r in res]
    assert scores == sorted(scores, reverse=True)
    assert all(0 <= r.score <= 100 for r in res)
