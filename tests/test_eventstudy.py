"""이벤트 스터디 하네스 검증.

측정 도구 자체가 믿을 만한지 먼저 확인한다. 두 가지가 핵심이다.

  1) **거짓양성을 내지 않는가** — 순수 랜덤워크(예측 불가능)에서 "예측력 있음"
     이라고 하면 안 된다.
  2) **참양성을 잡아내는가** — 점수가 미래 수익률을 설계상 예측하도록 만든
     인공 데이터에서는 반드시 강한 양(+)의 IC 가 나와야 한다.

2번이 없으면 하네스가 그냥 항상 "예측력 없음"을 뱉는 고장난 저울일 수 있다.
"""
from __future__ import annotations

import zlib

import numpy as np
import pandas as pd
import pytest

from stocksystem.analysis import technical as ta
from stocksystem.config import Config
from stocksystem.data.base import DataProvider
from stocksystem.research import eventstudy as es


def _stable_hash(s: str) -> int:
    """실행 간 재현 가능한 해시.

    내장 hash() 는 PYTHONHASHSEED 로 매 프로세스마다 달라져서, 그걸 시드로
    쓰면 인공 데이터가 실행마다 바뀌고 테스트가 flaky 해진다. 검증 하네스의
    테스트가 불안정하면 하네스를 신뢰할 근거가 사라진다.
    """
    return zlib.crc32(s.encode()) % 10_000


def ta_compute(provider, cfg):
    """공급자에서 지표가 계산된 프레임 하나를 뽑는 헬퍼."""
    return ta.compute_indicators(provider.price_history("S00"), cfg.technical)


# ----------------------------- 인공 공급자 -----------------------------
class _RandomWalkProvider(DataProvider):
    """기하 브라운 운동. 미래 수익률은 과거와 독립 → 예측 불가능해야 정상."""

    def __init__(self, n_days: int = 900, seed: int = 0):
        self.n_days = n_days
        self.seed = seed

    def _series(self, symbol: str) -> pd.DataFrame:
        rng = np.random.default_rng(self.seed + _stable_hash(symbol))
        idx = pd.bdate_range("2020-01-01", periods=self.n_days)
        ret = rng.normal(0.0004, 0.018, self.n_days)
        close = 100 * np.exp(np.cumsum(ret))
        return pd.DataFrame(
            {"Open": close, "High": close * 1.01, "Low": close * 0.99,
             "Close": close, "Volume": rng.integers(1e6, 5e6, self.n_days)},
            index=idx)

    def price_history(self, symbol, period="1y", interval="1d"):
        return self._series(symbol)

    def fundamentals(self, symbol):
        raise NotImplementedError

    def news(self, symbol, limit=10):
        return []


class _MomentumProvider(_RandomWalkProvider):
    """추세가 실제로 이어지는 시장.

    수익률에 강한 양의 자기상관을 넣어 '오르던 게 계속 오른다'를 만든다.
    이러면 추세추종 점수(SMA교차·가격위치·MACD)가 미래 수익률을 예측해야 하고,
    하네스는 그것을 반드시 잡아내야 한다.
    """

    def _series(self, symbol: str) -> pd.DataFrame:
        rng = np.random.default_rng(self.seed + _stable_hash(symbol))
        idx = pd.bdate_range("2020-01-01", periods=self.n_days)
        # AR(1) 수익률: phi 가 클수록 추세가 오래 간다
        phi, sigma = 0.85, 0.012
        eps = rng.normal(0, sigma, self.n_days)
        ret = np.zeros(self.n_days)
        for i in range(1, self.n_days):
            ret[i] = phi * ret[i - 1] + eps[i]
        close = 100 * np.exp(np.cumsum(ret))
        return pd.DataFrame(
            {"Open": close, "High": close * 1.01, "Low": close * 0.99,
             "Close": close, "Volume": rng.integers(1e6, 5e6, self.n_days)},
            index=idx)


SYMS = [f"S{i:02d}" for i in range(30)]
# 벤치마크는 반드시 유니버스 밖이어야 한다. 안에 넣으면 그 종목의 초과수익률이
# 항상 0 으로 고정돼 횡단면이 오염되고 IC 가 눌린다.
BENCH = "BENCH"


# ----------------------------- 통계 유틸 -----------------------------
def test_rank_ic_perfect_and_inverse():
    a = pd.Series([1, 2, 3, 4, 5], dtype=float)
    assert es._rank_ic(a, a) == pytest.approx(1.0)
    assert es._rank_ic(a, -a) == pytest.approx(-1.0)


def test_rank_ic_is_monotone_invariant():
    """순위상관이므로 단조변환에 불변이어야 한다."""
    a = pd.Series([1, 2, 3, 4, 5], dtype=float)
    b = pd.Series([10, 20, 30, 40, 50], dtype=float)
    assert es._rank_ic(a, b ** 3) == pytest.approx(1.0)


def test_rank_ic_handles_short_and_constant_input():
    assert np.isnan(es._rank_ic(pd.Series([1.0]), pd.Series([2.0])))
    const = pd.Series([5.0] * 6)
    assert np.isnan(es._rank_ic(const, pd.Series(range(6), dtype=float)))


def test_monotonicity_increasing_and_decreasing():
    assert es._monotonicity([-2.0, -1.0, 0.0, 1.0, 2.0]) == pytest.approx(1.0)
    assert es._monotonicity([2.0, 1.0, 0.0, -1.0, -2.0]) == pytest.approx(-1.0)


# ----------------------------- 룩어헤드 방지 -----------------------------
def test_forward_excess_has_no_lookahead():
    """t 행의 값은 t 이후 가격만 참조해야 하고, 마지막 h행은 NaN 이어야 한다."""
    idx = pd.bdate_range("2021-01-01", periods=30)
    close = pd.DataFrame({"X": np.arange(100.0, 130.0)}, index=idx)
    bench = pd.Series(np.full(30, 100.0), index=idx)   # 벤치마크 무변동
    ex = es.forward_excess(close, bench, horizon=5)

    assert ex["X"].tail(5).isna().all()          # 미래가 없으면 NaN
    # t=0: 100 → 105 = +5%, 벤치마크 0% → 초과 +5%p
    assert ex["X"].iloc[0] == pytest.approx(5.0)


def test_forward_excess_subtracts_benchmark():
    idx = pd.bdate_range("2021-01-01", periods=10)
    close = pd.DataFrame({"X": np.full(10, 100.0)}, index=idx)   # 종목 0%
    bench = pd.Series(np.linspace(100, 110, 10), index=idx)      # 벤치마크 상승
    ex = es.forward_excess(close, bench, horizon=3)
    assert ex["X"].iloc[0] < 0      # 벤치마크만 오르면 초과수익은 음수


# ----------------------------- 참양성 / 거짓양성 -----------------------------
def test_detects_real_signal_in_trending_market():
    """★ 핵심 — 신호가 실제로 있으면 하네스가 반드시 잡아내야 한다.

    수익률에 강한 양의 자기상관을 넣은 시장에서는 추세추종 점수가 미래
    수익률을 예측하는 게 설계상 보장된다. 여기서 유의성을 못 잡아내면
    하네스는 항상 '예측력 없음'만 뱉는 고장난 저울이다.
    """
    res = es.run_event_study(
        SYMS, _MomentumProvider(n_days=2500, seed=7), Config(),
        score_name="추세추종만", horizons=(20,), period="5y", benchmark=BENCH)
    h = res.horizons[20]
    assert h.ic_mean > 0.10, f"추세장에서 추세점수 IC 가 너무 낮음: {h.ic_mean}"
    assert h.significant, f"유의성을 잡아내지 못함 (t={h.ic_t})"
    assert h.monotonicity >= 0.7, f"구간이 단조 우상향하지 않음: {h.monotonicity}"
    assert h.long_short > 5.0, f"롱숏 스프레드가 너무 작음: {h.long_short}"
    assert "양(+)의 예측력" in res.verdict()


def test_no_false_positive_on_random_walk():
    """랜덤워크에서는 '유의한 예측력'을 주장하면 안 된다."""
    res = es.run_event_study(
        SYMS, _RandomWalkProvider(n_days=2500, seed=3), Config(),
        score_name="역추세만 (현행 기본)", horizons=(20,), period="5y",
        benchmark=BENCH)
    h = res.horizons[20]
    assert not h.significant, (
        f"랜덤워크인데 유의하다고 판정함: IC={h.ic_mean} t={h.ic_t}")
    assert "예측력 없음" in res.verdict()


def test_score_granularity_is_coarse():
    """점수가 몇 단계뿐인지 기록해 둔다 — 순위 도구로서의 해상도 한계.

    추세 신호 3개가 모두 이진(중립 없음)이라 추세점수는 4단계밖에 없다.
    타이가 많으면 순위상관이 구조적으로 눌린다.
    """
    cfg = Config()
    ind = ta_compute(_MomentumProvider(n_days=1200, seed=1), cfg)
    trend = ta.trend_score_series(ind, cfg.technical).dropna().unique()
    assert len(trend) <= 4, f"추세점수 단계 수가 예상과 다름: {sorted(trend)}"


def test_buckets_cover_all_observations():
    """구간 경계에 빈틈이 없어야 한다 (0~100 전 구간 커버)."""
    scores = pd.Series([0.0, 24.9, 25.0, 39.9, 40.0, 59.9, 60.0, 74.9,
                        75.0, 100.0])
    ret = pd.Series(np.arange(10.0))
    stats = es._bucketize(scores, ret, ret, es.DEFAULT_BANDS)
    assert sum(b.n for b in stats) == len(scores)


def test_bucket_stats_are_correct():
    scores = pd.Series([80.0, 80.0, 80.0, 80.0])
    excess = pd.Series([10.0, -5.0, 20.0, -1.0])
    stats = es._bucketize(scores, excess, excess, es.DEFAULT_BANDS)
    top = [b for b in stats if b.n][0]
    assert top.n == 4
    assert top.mean_excess == pytest.approx(6.0)
    assert top.hit_rate == pytest.approx(50.0)


# ----------------------------- 결과 객체 -----------------------------
def test_result_serializes_and_reports():
    res = es.run_event_study(
        SYMS[:6], _RandomWalkProvider(n_days=1500, seed=1), Config(),
        score_name="역추세만 (현행 기본)", horizons=(20, 60), period="5y",
        benchmark=BENCH)
    d = res.to_dict()
    assert set(d["horizons"]) == {"20", "60"}
    assert d["verdict"]
    assert len(d["warnings"]) >= 3            # 생존편향·펀더멘털·거래비용 경고
    text = res.report()
    assert "이벤트 스터디" in text and "판정:" in text


def test_missing_benchmark_raises_clear_error():
    class _NoBench(_RandomWalkProvider):
        def price_history(self, symbol, period="1y", interval="1d"):
            if symbol == "SPY":
                raise ValueError("no data")
            return self._series(symbol)

    with pytest.raises(ValueError, match="벤치마크"):
        es.run_event_study(SYMS[:3], _NoBench(), Config(), horizons=(20,))


def test_unknown_scorer_raises():
    with pytest.raises(KeyError):
        es.run_event_study(SYMS[:3], _RandomWalkProvider(), Config(),
                           score_name="없는점수", benchmark=BENCH)


def test_compare_scorers_runs_all():
    out = es.compare_scorers(SYMS[:8], _MomentumProvider(n_days=2000, seed=5), Config(),
                             horizons=(20,), period="5y", benchmark=BENCH)
    assert set(out) == set(es.SCORERS)
    # 추세장이므로 추세추종이 역추세보다 IC 가 높아야 한다
    assert (out["추세추종만"].horizons[20].ic_mean
            > out["역추세만 (현행 기본)"].horizons[20].ic_mean)


# ----------------------------- 다중검정 보정 -----------------------------
def test_bonferroni_threshold_grows_with_test_count():
    """가설이 많아질수록 임계값이 엄격해져야 한다."""
    assert es.bonferroni_t(1) == pytest.approx(1.96, abs=0.01)
    assert es.bonferroni_t(6) == pytest.approx(2.64, abs=0.01)
    assert es.bonferroni_t(1) < es.bonferroni_t(3) < es.bonferroni_t(12)


def test_bonferroni_handles_degenerate_counts():
    assert es.bonferroni_t(0) == es.bonferroni_t(1)
    assert es.bonferroni_t(-5) == es.bonferroni_t(1)


def test_marginal_result_fails_correction():
    """t=2.24 는 단일 가설이면 유의하지만 가설 6개에서는 살아남지 못한다.

    실측에서 '역추세만'이 정확히 이 상황이었다. 보정 없이 ✓ 를 믿으면
    잡음을 발견으로 착각한다.
    """
    t_observed = 2.24
    assert t_observed >= 2.0                      # 보정 전 기준은 통과
    assert t_observed < es.bonferroni_t(6)        # 보정 후 기준은 미달


# ----------------------------- 유니버스 편향 제거 -----------------------------
def test_demean_removes_common_drift():
    """모든 종목이 함께 오른 만큼은 신호의 공로가 아니다."""
    idx = pd.bdate_range("2021-01-01", periods=3)
    ex = pd.DataFrame({"A": [10.0, 10.0, 10.0],
                       "B": [10.0, 10.0, 10.0],
                       "C": [10.0, 10.0, 10.0]}, index=idx)
    out = es.demean_cross_section(ex)
    assert (out.abs() < 1e-9).all().all()   # 공통 상승은 전부 제거


def test_demean_preserves_relative_spread():
    idx = pd.bdate_range("2021-01-01", periods=2)
    ex = pd.DataFrame({"A": [12.0, 22.0], "B": [8.0, 18.0]}, index=idx)
    out = es.demean_cross_section(ex)
    # 원래 격차 4%p 는 그대로, 공통 수준(10, 20)만 사라진다
    assert out["A"].tolist() == pytest.approx([2.0, 2.0])
    assert out["B"].tolist() == pytest.approx([-2.0, -2.0])


def test_demean_is_per_date_not_global():
    """날짜마다 다른 시장 수익률을 각각 제거해야 한다."""
    idx = pd.bdate_range("2021-01-01", periods=2)
    ex = pd.DataFrame({"A": [1.0, 100.0], "B": [-1.0, 98.0]}, index=idx)
    out = es.demean_cross_section(ex)
    assert out.loc[idx[1], "A"] == pytest.approx(1.0)   # 둘째 날 평균 99 제거


def test_universe_bias_is_recorded_and_removed():
    """유니버스 평균이 기록되고, 편향제거 값이 그만큼 낮아져야 한다.

    구간별 편향제거 값은 `평균초과 − 유니버스평균` 과 정확히 같지는 않다.
    날짜마다 다른 시장 수익률을 각각 빼기 때문이고, 그게 전역 상수를 빼는
    것보다 정확하다. 여기서는 방향만 검증한다.
    """
    res = es.run_event_study(
        SYMS, _MomentumProvider(n_days=2000, seed=11), Config(),
        score_name="추세추종만", horizons=(20,), period="5y", benchmark=BENCH)
    h = res.horizons[20]
    assert h.universe_mean == h.universe_mean           # NaN 아님
    filled = [b for b in h.buckets if b.n]
    assert filled
    # 유니버스 평균만큼 전반적으로 낮아진다
    for b in filled:
        assert b.mean_demeaned < b.mean_excess or h.universe_mean <= 0
    # 편향제거 가중평균은 0 에 가까워야 한다 (공통 성분이 사라졌으므로)
    tot = sum(b.n for b in filled)
    wavg = sum(b.mean_demeaned * b.n for b in filled) / tot
    assert abs(wavg) < 0.5


def test_demeaned_long_short_is_recorded_and_can_differ():
    """편향제거 롱숏은 원시 롱숏과 다를 수 있다 — 그게 핵심이다.

    추세 점수는 상승장에 최상위 구간이, 하락장에 최하위 구간이 몰린다.
    원시 스프레드는 '신호의 힘'과 '구간이 채워지는 시점의 시장 상황'을
    섞어버리므로, 날짜별로 보정한 쪽이 신호의 순수 기여분이다.
    """
    res = es.run_event_study(
        SYMS, _MomentumProvider(n_days=2000, seed=11), Config(),
        score_name="추세추종만", horizons=(20,), period="5y", benchmark=BENCH)
    h = res.horizons[20]
    assert h.long_short_demeaned == h.long_short_demeaned   # NaN 아님
    # 수익 계산은 편향제거 쪽을 쓴다
    assert h.spread == h.long_short_demeaned
    assert h.breakeven_cost == pytest.approx(h.long_short_demeaned / 2)


# ----------------------------- 거래비용 -----------------------------
def test_annualized_long_short_scales_by_horizon():
    h20 = es.HorizonResult(horizon=20, buckets=[], ic_mean=0, ic_std=0,
                           ic_t=0, n_dates=1, n_obs=1, long_short=1.0,
                           monotonicity=0)
    h60 = es.HorizonResult(horizon=60, buckets=[], ic_mean=0, ic_std=0,
                           ic_t=0, n_dates=1, n_obs=1, long_short=1.0,
                           monotonicity=0)
    # 같은 스프레드라도 20일 구간이 연 3배 더 자주 반복된다
    assert h20.annualized_long_short() == pytest.approx(
        3 * h60.annualized_long_short(), rel=1e-6)


def test_transaction_cost_eats_into_return():
    h = es.HorizonResult(horizon=20, buckets=[], ic_mean=0, ic_std=0, ic_t=0,
                         n_dates=1, n_obs=1, long_short=0.343, monotonicity=0)
    assert h.annualized_long_short() > h.annualized_long_short(0.05) > \
        h.annualized_long_short(0.10)


def test_breakeven_cost_zeroes_the_return():
    """손익분기 비용을 물리면 정확히 0 이 돼야 한다."""
    h = es.HorizonResult(horizon=20, buckets=[], ic_mean=0, ic_std=0, ic_t=0,
                         n_dates=1, n_obs=1, long_short=0.343, monotonicity=0)
    assert h.annualized_long_short(h.breakeven_cost) == pytest.approx(0.0)


def test_cost_metrics_are_nan_safe():
    h = es.HorizonResult(horizon=20, buckets=[], ic_mean=0, ic_std=0, ic_t=0,
                         n_dates=1, n_obs=1, long_short=float("nan"),
                         monotonicity=0)
    assert h.breakeven_cost != h.breakeven_cost
    assert h.annualized_long_short() != h.annualized_long_short()


def test_report_and_dict_include_new_metrics():
    res = es.run_event_study(
        SYMS[:8], _RandomWalkProvider(n_days=1500, seed=2), Config(),
        score_name="역추세만 (현행 기본)", horizons=(20,), period="5y",
        benchmark=BENCH)
    d = res.to_dict()["horizons"]["20"]
    for k in ("universe_mean", "breakeven_cost", "annual_long_short_gross",
              "annual_long_short_net_5bp"):
        assert k in d
    assert "mean_demeaned" in d["buckets"][0]
    text = res.report()
    assert "편향제거" in text and "손익분기" in text


def test_scorers_have_no_duplicate_series():
    """★ 스코어러끼리 완전히 같은 시계열이면 안 된다.

    trend_weight 기본값이 0.0 이 되면서 '현행 설정' 점수가 '역추세만' 과
    똑같아졌다. 중복 행은 비교표를 오해하게 만들고, 다중검정 가설 수만 늘려
    Bonferroni 임계값을 불필요하게 엄격하게 만든다.
    """
    from stocksystem.config import Config as C
    cfg = C()
    ind = ta_compute(_MomentumProvider(n_days=800, seed=4), cfg)
    series = {n: fn(ind, cfg.technical).dropna() for n, fn in es.SCORERS.items()}
    names = list(series)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            assert not series[a].equals(series[b]), f"{a} 와 {b} 가 동일"


def test_default_scorer_matches_shipped_config():
    """기본 스코어러는 실제 배포 설정의 점수와 같아야 한다."""
    from stocksystem.config import load_config
    cfg = load_config()
    assert cfg.technical.trend_weight == 0.0
    ind = ta_compute(_RandomWalkProvider(n_days=600, seed=6), cfg)
    shipped = ta.score_series(ind, cfg.technical).dropna()
    default_scorer = es.SCORERS["역추세만 (현행 기본)"](ind, cfg.technical).dropna()
    assert shipped.equals(default_scorer)
