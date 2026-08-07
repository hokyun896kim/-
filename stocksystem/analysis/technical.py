"""기술적 분석 모듈.

순수 pandas/numpy 로 주요 지표를 계산하고, 각 지표를 0~100 점으로
환산해 종합 기술 점수를 만든다. (외부 TA 라이브러리 불필요)

지표:
- SMA(단기/장기), EMA
- RSI (상대강도지수)
- MACD (이동평균수렴확산)
- 볼린저밴드
- 거래량 추세
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..config import TechnicalConfig


# ----------------------------- 개별 지표 -----------------------------
def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Wilder 방식 RSI."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    # 손실이 0이면 RSI=100
    out = out.where(avg_loss != 0, 100.0)
    return out


def macd(series: pd.Series, fast: int = 12, slow: int = 26,
         signal: int = 9) -> pd.DataFrame:
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return pd.DataFrame({"macd": macd_line, "signal": signal_line, "hist": hist})


def bollinger(series: pd.Series, period: int = 20,
              num_std: float = 2.0) -> pd.DataFrame:
    mid = sma(series, period)
    std = series.rolling(window=period, min_periods=period).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    # %B: 밴드 내 위치 (0=하단, 1=상단)
    pct_b = (series - lower) / (upper - lower)
    return pd.DataFrame({"bb_mid": mid, "bb_upper": upper,
                         "bb_lower": lower, "bb_pct": pct_b})


# ----------------------------- 종합 -----------------------------
# 신호의 성격 분류.
#
# 이 둘은 철학이 정반대다. 추세추종은 "오를수록 사라", 역추세는 "빠질수록 사라"
# 라고 말한다. 기존 score_series() 는 다섯을 그냥 산술평균했기 때문에, 강하게
# 오르는 종목은 역추세 신호에 20점 깎이고 급락 중인 종목은 20점 얹어 받았다.
# 어느 쪽이 실제로 수익을 냈는지는 stocksystem.research.eventstudy 로 측정한다.
TREND_SIGNALS = ("추세(SMA교차)", "가격위치", "MACD")
REVERSION_SIGNALS = ("RSI", "볼린저")


@dataclass
class TechnicalResult:
    symbol: str
    score: float                       # 0~100 종합 기술 점수
    indicators: pd.DataFrame           # 지표가 붙은 가격 DataFrame
    signals: dict[str, str] = field(default_factory=dict)  # 지표별 매수/중립/매도
    latest: dict[str, float] = field(default_factory=dict) # 최신 지표 값
    trend_score: float | None = None      # 추세추종 신호만의 점수
    reversion_score: float | None = None  # 역추세 신호만의 점수


def compute_indicators(df: pd.DataFrame, cfg: TechnicalConfig) -> pd.DataFrame:
    """가격 DataFrame 에 모든 지표 컬럼을 추가한다."""
    out = df.copy()
    close = out["Close"]
    out[f"SMA{cfg.sma_short}"] = sma(close, cfg.sma_short)
    out[f"SMA{cfg.sma_long}"] = sma(close, cfg.sma_long)
    out[f"EMA{cfg.ema_period}"] = ema(close, cfg.ema_period)
    out["RSI"] = rsi(close, cfg.rsi_period)
    out = out.join(macd(close, cfg.macd_fast, cfg.macd_slow, cfg.macd_signal))
    out = out.join(bollinger(close, cfg.bb_period, cfg.bb_std))
    out["VOL_SMA"] = sma(out["Volume"], 20)
    return out


def _score_from_signals(signals: dict[str, str]) -> float:
    """매수=1, 중립=0.5, 매도=0 평균을 0~100 으로 환산."""
    mapping = {"buy": 1.0, "neutral": 0.5, "sell": 0.0}
    vals = [mapping[s] for s in signals.values()]
    if not vals:
        return 50.0
    return round(float(np.mean(vals)) * 100, 1)


def signal_frame(ind: pd.DataFrame, cfg: TechnicalConfig) -> pd.DataFrame:
    """각 지표 신호를 시계열로 벡터화한다 (매수=1, 중립=0.5, 매도=0).

    analyze() 의 단일 시점 로직을 전체 기간으로 확장한 것.
    지표가 NaN 인 구간은 NaN (점수 계산에서 제외).
    """
    close = ind["Close"]
    s_short, s_long = ind[f"SMA{cfg.sma_short}"], ind[f"SMA{cfg.sma_long}"]
    out = pd.DataFrame(index=ind.index)

    # 1) 추세(SMA 교차): 단기>장기 → 매수
    out["추세(SMA교차)"] = np.where(s_short > s_long, 1.0, 0.0)
    out.loc[s_short.isna() | s_long.isna(), "추세(SMA교차)"] = np.nan
    # 2) 가격위치: 종가 > 장기이평 → 매수
    out["가격위치"] = np.where(close > s_long, 1.0, 0.0)
    out.loc[s_long.isna(), "가격위치"] = np.nan
    # 3) RSI: 과매도 매수 / 과매수 매도 / 그 외 중립
    rsi_v = ind["RSI"]
    out["RSI"] = np.where(rsi_v < cfg.rsi_oversold, 1.0,
                          np.where(rsi_v > cfg.rsi_overbought, 0.0, 0.5))
    out.loc[rsi_v.isna(), "RSI"] = np.nan
    # 4) MACD 히스토그램 부호
    out["MACD"] = np.where(ind["hist"] > 0, 1.0, 0.0)
    out.loc[ind["hist"].isna(), "MACD"] = np.nan
    # 5) 볼린저 %B
    pct = ind["bb_pct"]
    out["볼린저"] = np.where(pct < 0.2, 1.0, np.where(pct > 0.8, 0.0, 0.5))
    out.loc[pct.isna(), "볼린저"] = np.nan
    return out


def _subset_score(sf: pd.DataFrame, names) -> pd.Series:
    """signal_frame 의 일부 컬럼만으로 0~100 점수 시계열을 만든다."""
    cols = [c for c in names if c in sf.columns]
    if not cols:
        return pd.Series(np.nan, index=sf.index)
    return sf[cols].mean(axis=1, skipna=True) * 100


def trend_score_series(ind: pd.DataFrame, cfg: TechnicalConfig) -> pd.Series:
    """추세추종 신호(SMA교차·가격위치·MACD)만의 점수 시계열."""
    return _subset_score(signal_frame(ind, cfg), TREND_SIGNALS)


def reversion_score_series(ind: pd.DataFrame, cfg: TechnicalConfig) -> pd.Series:
    """역추세 신호(RSI·볼린저)만의 점수 시계열."""
    return _subset_score(signal_frame(ind, cfg), REVERSION_SIGNALS)


def score_series(ind: pd.DataFrame, cfg: TechnicalConfig,
                 trend_weight: float | None = None) -> pd.Series:
    """기간 전체에 대한 기술 종합점수(0~100) 시계열.

    trend_weight=None (기본): 가용한 다섯 신호의 단순평균 — 기존 동작 그대로.
    trend_weight=w  (0~1)   : 추세 w · 역추세 (1-w) 로 가중. w=1.0 이면 순수
                              추세추종, w=0.0 이면 순수 역추세가 된다.

    analyze().score 와 마지막 값이 일치한다 (trend_weight=None 일 때).
    """
    sf = signal_frame(ind, cfg)
    if trend_weight is None:
        return sf.mean(axis=1, skipna=True) * 100
    w = float(min(max(trend_weight, 0.0), 1.0))
    tr = _subset_score(sf, TREND_SIGNALS)
    rv = _subset_score(sf, REVERSION_SIGNALS)
    # 가용한 쪽의 가중치만 남기고 재정규화한다.
    #
    # MACD 는 첫날부터 값이 있지만 RSI·볼린저는 14~20일이 지나야 나온다.
    # 그래서 초반 구간엔 추세만 존재하는데, 여기서 "없는 쪽을 있는 쪽으로
    # 메우는" 식으로 처리하면 trend_weight=0(순수 역추세)인데도 추세 점수가
    # 새어 들어온다. 가중치가 0인 성분은 절대 결과에 들어가면 안 된다.
    wt = pd.Series(np.where(tr.notna(), w, 0.0), index=sf.index)
    wr = pd.Series(np.where(rv.notna(), 1.0 - w, 0.0), index=sf.index)
    total = wt + wr
    num = tr.fillna(0.0) * wt + rv.fillna(0.0) * wr
    return (num / total).where(total > 0)


def analyze(df: pd.DataFrame, cfg: TechnicalConfig,
            symbol: str = "") -> TechnicalResult:
    """기술적 분석을 수행하고 종합 점수/신호를 반환한다."""
    ind = compute_indicators(df, cfg)
    last = ind.iloc[-1]
    signals: dict[str, str] = {}

    # 1) 추세: 단기 SMA vs 장기 SMA (골든/데드크로스)
    s_short, s_long = last[f"SMA{cfg.sma_short}"], last[f"SMA{cfg.sma_long}"]
    if pd.notna(s_short) and pd.notna(s_long):
        signals["추세(SMA교차)"] = "buy" if s_short > s_long else "sell"

    # 2) 가격 vs 장기 이평
    if pd.notna(s_long):
        signals["가격위치"] = "buy" if last["Close"] > s_long else "sell"

    # 3) RSI
    r = last["RSI"]
    if pd.notna(r):
        if r < cfg.rsi_oversold:
            signals["RSI"] = "buy"        # 과매도 → 반등 기대
        elif r > cfg.rsi_overbought:
            signals["RSI"] = "sell"       # 과매수 → 조정 우려
        else:
            signals["RSI"] = "neutral"

    # 4) MACD 히스토그램 부호
    h = last["hist"]
    if pd.notna(h):
        signals["MACD"] = "buy" if h > 0 else "sell"

    # 5) 볼린저밴드 %B
    pct = last["bb_pct"]
    if pd.notna(pct):
        if pct < 0.2:
            signals["볼린저"] = "buy"      # 하단 근접 → 저평가 구간
        elif pct > 0.8:
            signals["볼린저"] = "sell"     # 상단 근접 → 고평가 구간
        else:
            signals["볼린저"] = "neutral"

    score = _score_from_signals(signals)
    trend_s = _score_from_signals(
        {k: v for k, v in signals.items() if k in TREND_SIGNALS}) \
        if any(k in signals for k in TREND_SIGNALS) else None
    rev_s = _score_from_signals(
        {k: v for k, v in signals.items() if k in REVERSION_SIGNALS}) \
        if any(k in signals for k in REVERSION_SIGNALS) else None
    latest = {
        "close": float(last["Close"]),
        "rsi": float(r) if pd.notna(r) else float("nan"),
        "macd_hist": float(h) if pd.notna(h) else float("nan"),
        "bb_pct": float(pct) if pd.notna(pct) else float("nan"),
        f"sma{cfg.sma_short}": float(s_short) if pd.notna(s_short) else float("nan"),
        f"sma{cfg.sma_long}": float(s_long) if pd.notna(s_long) else float("nan"),
    }
    return TechnicalResult(symbol=symbol, score=score, indicators=ind,
                           signals=signals, latest=latest,
                           trend_score=trend_s, reversion_score=rev_s)
