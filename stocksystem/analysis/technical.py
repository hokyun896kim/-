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
@dataclass
class TechnicalResult:
    symbol: str
    score: float                       # 0~100 종합 기술 점수
    indicators: pd.DataFrame           # 지표가 붙은 가격 DataFrame
    signals: dict[str, str] = field(default_factory=dict)  # 지표별 매수/중립/매도
    latest: dict[str, float] = field(default_factory=dict) # 최신 지표 값


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
    latest = {
        "close": float(last["Close"]),
        "rsi": float(r) if pd.notna(r) else float("nan"),
        "macd_hist": float(h) if pd.notna(h) else float("nan"),
        "bb_pct": float(pct) if pd.notna(pct) else float("nan"),
        f"sma{cfg.sma_short}": float(s_short) if pd.notna(s_short) else float("nan"),
        f"sma{cfg.sma_long}": float(s_long) if pd.notna(s_long) else float("nan"),
    }
    return TechnicalResult(symbol=symbol, score=score, indicators=ind,
                           signals=signals, latest=latest)
