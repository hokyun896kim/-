"""백테스트 전략 모음.

각 전략은 지표가 계산된 DataFrame(ind)과 설정을 받아 '목표 포지션' 시계열을
돌려준다. 1.0 = 풀매수(롱), 0.0 = 현금(관망). 단순/직관적인 롱온리 방식.

개인투자자가 이해하기 쉬운 대표 전략 4종:
- sma_crossover : 골든크로스에 사고 데드크로스에 판다 (추세추종)
- rsi_reversion : 과매도에 사고 과매수에 판다 (역추세/단기반등)
- macd_signal   : MACD 히스토그램이 0을 상향 돌파하면 매수
- score_threshold: 시스템 종합 기술점수가 기준선을 넘으면 매수 (히스테리시스)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..config import TechnicalConfig
from ..analysis import technical as ta


def sma_crossover(ind: pd.DataFrame, cfg: TechnicalConfig) -> pd.Series:
    s_short, s_long = ind[f"SMA{cfg.sma_short}"], ind[f"SMA{cfg.sma_long}"]
    pos = (s_short > s_long).astype(float)
    pos[s_short.isna() | s_long.isna()] = 0.0
    return pos


def rsi_reversion(ind: pd.DataFrame, cfg: TechnicalConfig) -> pd.Series:
    """RSI 과매도(<oversold) 진입, 과매수(>overbought) 청산. 중간은 유지."""
    rsi = ind["RSI"]
    target = pd.Series(np.nan, index=ind.index)
    target[rsi < cfg.rsi_oversold] = 1.0
    target[rsi > cfg.rsi_overbought] = 0.0
    return target.ffill().fillna(0.0)


def macd_signal(ind: pd.DataFrame, cfg: TechnicalConfig) -> pd.Series:
    pos = (ind["hist"] > 0).astype(float)
    pos[ind["hist"].isna()] = 0.0
    return pos


def score_threshold(ind: pd.DataFrame, cfg: TechnicalConfig,
                    buy: float = 60.0, sell: float = 40.0) -> pd.Series:
    """종합 기술점수 >= buy 면 진입, <= sell 이면 청산, 그 사이는 유지.

    매매가 너무 잦지 않도록 히스테리시스(이중 기준선)를 둔다.
    """
    score = ta.score_series(ind, cfg)
    target = pd.Series(np.nan, index=ind.index)
    target[score >= buy] = 1.0
    target[score <= sell] = 0.0
    return target.ffill().fillna(0.0)


# 대시보드/CLI 노출용 레지스트리
STRATEGIES = {
    "골든크로스 (SMA 교차)": sma_crossover,
    "RSI 역추세": rsi_reversion,
    "MACD 추세": macd_signal,
    "종합 기술점수": score_threshold,
}
