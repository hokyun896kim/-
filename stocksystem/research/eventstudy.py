"""이벤트 스터디 — 점수의 예측력을 측정한다.

핵심 질문: **"종합점수 80점 종목이 20점 종목보다 실제로 더 올랐는가?"**

측정 방법
---------
1. 유니버스 각 종목의 과거 일별 점수 시계열을 만든다 (t 시점 데이터만 사용).
2. t 시점 점수 → t~t+h 구간의 **벤치마크 대비 초과수익률**을 짝짓는다.
3. 점수 구간(추천 등급 경계와 동일)별 평균 초과수익률·승률을 집계한다.
4. 날짜별 횡단면 **순위상관(IC)** 과 그 t값으로 통계적 유의성을 본다.

편향 방지
---------
- **룩어헤드**: 점수는 t 시점까지의 데이터로만 계산하고, 수익률은 t 이후
  구간만 쓴다. 겹치는 지점이 없다.
- **중복표본**: 일별로 h일 수익률을 쓰면 구간이 h-1일씩 겹쳐 표본이 부풀고
  t값이 과대평가된다. 그래서 기본적으로 **h일 간격으로 샘플링(stride=h)**해
  구간이 겹치지 않게 한다.
- **생존편향**: 현재 상장된 종목만 담긴 universe.csv 를 쓰므로 상장폐지 종목이
  빠져 있다. 결과는 낙관 쪽으로 치우친다 — 리포트에 경고로 명시한다.

한계
----
펀더멘털 점수는 여기서 측정할 수 없다. yfinance `.info` 는 **현재 시점의**
PER/ROE 만 주기 때문에 과거 특정일의 펀더멘털을 복원할 수 없다 (point-in-time
데이터 부재). 따라서 이 하네스는 **기술 점수 계열만** 정직하게 검증한다.
종합점수의 펀더멘털 절반은 별도 데이터원(SEC XBRL 등) 없이는 검증 불가다.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..analysis import technical as ta
from ..config import Config
from ..data.base import DataProvider

# 점수 구간 — 앱의 추천 등급 경계와 동일하게 잡아 "적극매수가 정말 더 올랐나"를
# 직접 답할 수 있게 한다. (하한 포함, 상한 미포함. 마지막 구간만 100 포함)
DEFAULT_BANDS = [
    ("적극매도 (0~25)", 0.0, 25.0),
    ("매도 (25~40)", 25.0, 40.0),
    ("보유 (40~60)", 40.0, 60.0),
    ("매수 (60~75)", 60.0, 75.0),
    ("적극매수 (75~100)", 75.0, 100.01),
]

# 검증 대상 점수들. 추세/역추세를 따로 재야 어느 쪽이 수익을 냈는지 알 수 있다.
SCORERS = {
    "종합기술점수(현행)": lambda ind, cfg: ta.score_series(ind, cfg),
    "추세추종만": lambda ind, cfg: ta.trend_score_series(ind, cfg),
    "역추세만": lambda ind, cfg: ta.reversion_score_series(ind, cfg),
}


# ----------------------------- 통계 유틸 -----------------------------
def _rank_ic(scores: pd.Series, rets: pd.Series) -> float:
    """스피어만 순위상관. scipy 없이 순위 → 피어슨으로 계산한다."""
    both = pd.concat([scores, rets], axis=1).dropna()
    if len(both) < 3:
        return float("nan")
    a = both.iloc[:, 0].rank()
    b = both.iloc[:, 1].rank()
    if a.std() == 0 or b.std() == 0:
        return float("nan")
    return float(np.corrcoef(a.to_numpy(), b.to_numpy())[0, 1])


def _monotonicity(means: list[float]) -> float:
    """구간 순서 대비 평균수익률의 순위상관. 1.0 이면 완벽한 단조 증가."""
    vals = [(i, m) for i, m in enumerate(means) if m == m]  # NaN 제외
    if len(vals) < 3:
        return float("nan")
    idx = pd.Series([v[0] for v in vals], dtype=float)
    mean = pd.Series([v[1] for v in vals], dtype=float)
    return _rank_ic(idx, mean)


# ----------------------------- 결과 자료구조 -----------------------------
@dataclass
class BucketStat:
    label: str
    lo: float
    hi: float
    n: int                     # 표본 수 (종목-일 관측치)
    mean_excess: float         # 평균 초과수익률 (%)
    median_excess: float
    hit_rate: float            # 초과수익 > 0 비율 (%)
    mean_raw: float            # 벤치마크 차감 전 평균 수익률 (%)


@dataclass
class HorizonResult:
    horizon: int               # 예측 구간 (거래일)
    buckets: list[BucketStat]
    ic_mean: float             # 날짜별 횡단면 IC 평균
    ic_std: float
    ic_t: float                # t = mean / (std / sqrt(n_dates))
    n_dates: int               # 독립적인(겹치지 않는) 관측 날짜 수
    n_obs: int                 # 전체 종목-일 관측치
    long_short: float          # 최상위 구간 − 최하위 구간 (%p)
    monotonicity: float        # 구간이 순서대로 우상향하는가 (-1~1)

    @property
    def significant(self) -> bool:
        """|t| >= 2 를 통상적인 유의 기준으로 본다."""
        return self.ic_t == self.ic_t and abs(self.ic_t) >= 2.0


@dataclass
class EventStudyResult:
    score_name: str
    symbols: list[str] = field(default_factory=list)
    benchmark: str = "SPY"
    start: str = ""
    end: str = ""
    stride: int | None = None      # None = horizon 과 동일 (구간 비중첩)
    horizons: dict[int, HorizonResult] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def stride_label(self) -> str:
        return "horizon과 동일(비중첩)" if not self.stride else f"{self.stride}일"

    # ---- 판정 ----
    def verdict(self) -> str:
        """가장 긴 구간을 기준으로 한 줄 판정."""
        if not self.horizons:
            return "판정 불가 — 표본 없음"
        h = self.horizons[max(self.horizons)]
        if h.ic_t != h.ic_t:
            return "판정 불가 — 표본 부족"
        if not h.significant:
            return (f"❌ 예측력 없음 — IC {h.ic_mean:+.3f} (t={h.ic_t:+.2f}), "
                    f"유의하지 않음. 이 점수로 매매하면 안 됩니다.")
        if h.ic_mean > 0:
            return (f"✅ 양(+)의 예측력 — IC {h.ic_mean:+.3f} "
                    f"(t={h.ic_t:+.2f}), 롱숏 {h.long_short:+.2f}%p. "
                    f"높은 점수가 실제로 더 올랐습니다.")
        return (f"⚠️ 음(−)의 예측력 — IC {h.ic_mean:+.3f} (t={h.ic_t:+.2f}). "
                f"점수가 높을수록 오히려 덜 올랐습니다. 신호를 뒤집어야 합니다.")

    def to_dict(self) -> dict:
        return {
            "score_name": self.score_name,
            "benchmark": self.benchmark,
            "symbols": self.symbols,
            "n_symbols": len(self.symbols),
            "start": self.start,
            "end": self.end,
            "stride": self.stride_label,
            "verdict": self.verdict(),
            "warnings": self.warnings,
            "horizons": {
                str(h): {
                    "horizon": r.horizon,
                    "ic_mean": None if r.ic_mean != r.ic_mean else round(r.ic_mean, 4),
                    "ic_t": None if r.ic_t != r.ic_t else round(r.ic_t, 2),
                    "n_dates": r.n_dates,
                    "n_obs": r.n_obs,
                    "long_short": None if r.long_short != r.long_short
                    else round(r.long_short, 3),
                    "monotonicity": None if r.monotonicity != r.monotonicity
                    else round(r.monotonicity, 3),
                    "significant": r.significant,
                    "buckets": [
                        {"label": b.label, "n": b.n,
                         "mean_excess": None if b.mean_excess != b.mean_excess
                         else round(b.mean_excess, 3),
                         "median_excess": None if b.median_excess != b.median_excess
                         else round(b.median_excess, 3),
                         "hit_rate": None if b.hit_rate != b.hit_rate
                         else round(b.hit_rate, 1),
                         "mean_raw": None if b.mean_raw != b.mean_raw
                         else round(b.mean_raw, 3)}
                        for b in r.buckets
                    ],
                }
                for h, r in sorted(self.horizons.items())
            },
        }

    def report(self) -> str:
        """터미널용 텍스트 리포트."""
        L = []
        L.append("═" * 74)
        L.append(f" 이벤트 스터디: {self.score_name}")
        L.append("═" * 74)
        L.append(f" 유니버스 {len(self.symbols)}종목 · {self.start} ~ {self.end}"
                 f" · 벤치마크 {self.benchmark} · 샘플링 {self.stride_label}")
        L.append("")
        for h in sorted(self.horizons):
            r = self.horizons[h]
            L.append(f"── 향후 {h}거래일 " + "─" * 56)
            L.append(f"{'점수 구간':<20}{'표본':>7}{'평균초과':>10}"
                     f"{'중앙초과':>10}{'승률':>8}{'절대수익':>10}")
            L.append("─" * 74)
            for b in r.buckets:
                if b.n == 0:
                    L.append(f"{b.label:<20}{0:>7}{'—':>10}{'—':>10}"
                             f"{'—':>8}{'—':>10}")
                    continue
                L.append(f"{b.label:<20}{b.n:>7}{b.mean_excess:>+9.2f}%"
                         f"{b.median_excess:>+9.2f}%{b.hit_rate:>7.0f}%"
                         f"{b.mean_raw:>+9.2f}%")
            L.append("─" * 74)
            ic_s = "—" if r.ic_mean != r.ic_mean else f"{r.ic_mean:+.4f}"
            t_s = "—" if r.ic_t != r.ic_t else f"{r.ic_t:+.2f}"
            mono_s = ("—" if r.monotonicity != r.monotonicity
                      else f"{r.monotonicity:+.2f}")
            ls_s = ("—" if r.long_short != r.long_short
                    else f"{r.long_short:+.2f}%p")
            L.append(f"  IC(순위상관) {ic_s}   t값 {t_s}   "
                     f"단조성 {mono_s}   롱숏 {ls_s}")
            L.append(f"  독립 관측일 {r.n_dates}일 · 전체 관측치 {r.n_obs}개 · "
                     f"유의성 {'있음 ✓' if r.significant else '없음 ✗'}")
            L.append("")
        L.append("판정: " + self.verdict())
        if self.warnings:
            L.append("")
            L.append("⚠️ 주의사항")
            for w in self.warnings:
                L.append(f"  · {w}")
        L.append("═" * 74)
        return "\n".join(L)


# ----------------------------- 패널 구성 -----------------------------
def build_panel(symbols, provider: DataProvider, cfg: Config,
                period: str = "5y", scorers: dict | None = None,
                benchmark: str = "SPY", progress=None):
    """종목별 가격·점수 패널을 만든다.

    반환: (close: DataFrame[date, symbol], scores: dict[name, DataFrame],
           bench: Series, failed: list[str])
    """
    scorers = scorers or SCORERS
    closes: dict[str, pd.Series] = {}
    per_score: dict[str, dict[str, pd.Series]] = {n: {} for n in scorers}
    failed: list[str] = []

    todo = list(dict.fromkeys(list(symbols) + [benchmark]))
    for i, sym in enumerate(todo, 1):
        if progress:
            progress(i, len(todo), sym)
        try:
            df = provider.price_history(sym, period=period)
            ind = ta.compute_indicators(df, cfg.technical)
        except Exception:
            failed.append(sym)
            continue
        closes[sym] = ind["Close"].astype(float)
        if sym == benchmark and sym not in symbols:
            continue          # 벤치마크는 점수 대상에서 제외
        for name, fn in scorers.items():
            try:
                per_score[name][sym] = fn(ind, cfg.technical)
            except Exception:
                pass

    if benchmark not in closes:
        raise ValueError(
            f"벤치마크 '{benchmark}' 시세를 받지 못해 초과수익률을 계산할 수 "
            f"없습니다. --benchmark 로 다른 종목을 지정하거나 네트워크를 "
            f"확인하세요.")

    close_df = pd.DataFrame(closes).sort_index()
    # 타임존이 섞이면 정렬이 깨지므로 날짜로 정규화
    if isinstance(close_df.index, pd.DatetimeIndex) and close_df.index.tz:
        close_df.index = close_df.index.tz_localize(None)
    bench = close_df[benchmark]
    score_dfs = {}
    for name, cols in per_score.items():
        if not cols:
            continue
        sdf = pd.DataFrame(cols).sort_index()
        if isinstance(sdf.index, pd.DatetimeIndex) and sdf.index.tz:
            sdf.index = sdf.index.tz_localize(None)
        score_dfs[name] = sdf.reindex(close_df.index)
    return close_df, score_dfs, bench, failed


def forward_excess(close: pd.DataFrame, bench: pd.Series,
                   horizon: int) -> pd.DataFrame:
    """t → t+horizon 의 벤치마크 대비 초과수익률(%) 행렬.

    마지막 horizon 행은 미래 데이터가 없어 NaN 이 된다 (룩어헤드 없음).
    """
    fwd = close.shift(-horizon) / close - 1.0
    bfwd = bench.shift(-horizon) / bench - 1.0
    return (fwd.sub(bfwd, axis=0)) * 100.0


def forward_raw(close: pd.DataFrame, horizon: int) -> pd.DataFrame:
    return (close.shift(-horizon) / close - 1.0) * 100.0


# ----------------------------- 실행 -----------------------------
def _bucketize(scores: pd.Series, excess: pd.Series, raw: pd.Series,
               bands) -> list[BucketStat]:
    out = []
    for label, lo, hi in bands:
        m = (scores >= lo) & (scores < hi)
        e = excess[m].dropna()
        r = raw[m].dropna()
        if len(e) == 0:
            out.append(BucketStat(label, lo, hi, 0, float("nan"),
                                  float("nan"), float("nan"), float("nan")))
            continue
        out.append(BucketStat(
            label=label, lo=lo, hi=hi, n=int(len(e)),
            mean_excess=float(e.mean()),
            median_excess=float(e.median()),
            hit_rate=float((e > 0).mean() * 100),
            mean_raw=float(r.mean()) if len(r) else float("nan"),
        ))
    return out


def analyze_panel(panel, score_name: str, *, horizons=(20, 60),
                  benchmark: str = "SPY", bands=None,
                  stride: int | None = None) -> EventStudyResult:
    """이미 만들어둔 패널에서 점수 하나를 분석한다.

    시세 수집과 분석을 분리해 둔 이유: 여러 점수를 비교할 때 같은 시세를
    점수 개수만큼 다시 받는 낭비를 막기 위해서다. 80종목 × 3점수면
    240회가 80회로 줄고, Yahoo 429 위험도 그만큼 낮아진다.
    """
    close, score_dfs, bench, failed = panel
    bands = bands or DEFAULT_BANDS
    scores = score_dfs.get(score_name)
    if scores is None or scores.empty:
        raise ValueError("점수 패널이 비어 있습니다 — 시세를 받지 못했습니다.")

    used = [c for c in scores.columns]
    res = EventStudyResult(
        score_name=score_name, symbols=used, benchmark=benchmark,
        start=str(close.index[0].date()), end=str(close.index[-1].date()),
        stride=stride)

    for h in horizons:
        st = stride or h
        excess = forward_excess(close[used], bench, h)
        raw = forward_raw(close[used], h)
        # 겹치지 않게 st 간격으로만 표본을 취한다
        rows = np.arange(0, len(close.index), st)
        idx = close.index[rows]
        s_s = scores.loc[idx]
        e_s = excess.loc[idx]
        r_s = raw.loc[idx]

        # 세 프레임은 같은 index/columns 라 ravel 하면 (날짜,종목) 순서가 맞는다.
        # (stack() 은 pandas 버전마다 NA 처리가 달라 쓰지 않는다)
        flat_s = pd.Series(s_s.to_numpy(dtype=float).ravel())
        flat_e = pd.Series(e_s.to_numpy(dtype=float).ravel())
        flat_r = pd.Series(r_s.to_numpy(dtype=float).ravel())
        buckets = _bucketize(flat_s, flat_e, flat_r, bands)

        # 날짜별 횡단면 IC
        ics = []
        for d in idx:
            ic = _rank_ic(s_s.loc[d], e_s.loc[d])
            if ic == ic:
                ics.append(ic)
        ic_arr = np.array(ics, dtype=float)
        if len(ic_arr) >= 2:
            ic_mean = float(ic_arr.mean())
            ic_std = float(ic_arr.std(ddof=1))
            ic_t = (float(ic_mean / (ic_std / math.sqrt(len(ic_arr))))
                    if ic_std > 0 else float("nan"))
        else:
            ic_mean = ic_std = ic_t = float("nan")

        filled = [b for b in buckets if b.n > 0]
        long_short = (filled[-1].mean_excess - filled[0].mean_excess
                      if len(filled) >= 2 else float("nan"))

        res.horizons[h] = HorizonResult(
            horizon=h, buckets=buckets, ic_mean=ic_mean, ic_std=ic_std,
            ic_t=ic_t, n_dates=len(ic_arr),
            n_obs=int(e_s.notna().to_numpy().sum()),
            long_short=long_short,
            monotonicity=_monotonicity([b.mean_excess for b in buckets]))

    res.warnings.append(
        "생존편향: universe.csv 는 현재 상장 종목만 담고 있어 상장폐지 종목이 "
        "빠져 있습니다. 실제 성과는 여기 수치보다 나쁠 수 있습니다.")
    res.warnings.append(
        "펀더멘털 점수는 point-in-time 데이터가 없어 검증 대상에서 제외됩니다. "
        "따라서 앱의 '종합점수'(기술 50% + 펀더멘털 50%) 전체가 아니라 "
        "기술 절반만 측정한 결과입니다.")
    res.warnings.append(
        "거래비용·슬리피지·세금은 반영되지 않았습니다. 실현 가능한 수익은 "
        "이보다 낮습니다.")
    if failed:
        res.warnings.append(f"시세를 받지 못한 종목 {len(failed)}개: "
                            f"{', '.join(failed[:10])}"
                            + (" 외" if len(failed) > 10 else ""))
    return res


def run_event_study(symbols, provider: DataProvider, cfg: Config, *,
                    score_name: str = "종합기술점수(현행)",
                    horizons=(20, 60), period: str = "5y",
                    benchmark: str = "SPY", bands=None,
                    stride: int | None = None,
                    scorers: dict | None = None,
                    panel=None,
                    progress=None) -> EventStudyResult:
    """점수 하나에 대해 이벤트 스터디를 수행한다.

    stride: 샘플링 간격(거래일). None 이면 각 horizon 과 동일하게 잡아
            수익률 구간이 겹치지 않게 한다 (t값 과대평가 방지).
    panel:  build_panel() 결과를 넘기면 시세를 다시 받지 않는다.
    """
    scorers = scorers or SCORERS
    if score_name not in scorers:
        raise KeyError(f"알 수 없는 점수: {score_name}. "
                       f"가능한 값: {list(scorers)}")
    if panel is None:
        panel = build_panel(symbols, provider, cfg, period=period,
                            scorers={score_name: scorers[score_name]},
                            benchmark=benchmark, progress=progress)
    return analyze_panel(panel, score_name, horizons=horizons,
                         benchmark=benchmark, bands=bands, stride=stride)


def compare_scorers(symbols, provider: DataProvider, cfg: Config, *,
                    horizons=(20, 60), period: str = "5y",
                    benchmark: str = "SPY", scorers: dict | None = None,
                    bands=None, stride: int | None = None,
                    progress=None) -> dict[str, EventStudyResult]:
    """여러 점수를 **같은 시세 한 벌로** 비교한다 (추세 vs 역추세 판정용).

    build_panel 이 모든 점수를 한 번에 계산하므로 시세 수집은 1회뿐이다.
    """
    scorers = scorers or SCORERS
    panel = build_panel(symbols, provider, cfg, period=period,
                        scorers=scorers, benchmark=benchmark,
                        progress=progress)
    return {name: analyze_panel(panel, name, horizons=horizons,
                                benchmark=benchmark, bands=bands,
                                stride=stride)
            for name in scorers}
