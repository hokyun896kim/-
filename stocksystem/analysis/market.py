"""시장(지수) 분석 모듈.

S&P 500 · 나스닥 같은 주요 지수를 주도면밀하게 분석한다. 개별 종목보다
'추세 국면 + 수급 + 변동성 + 주요 레벨 + 방향성 시나리오'에 초점을 둔다.

핵심 산출물:
- 추세(50/200일선, 골든/데드크로스, 200일선 대비 위치)
- 모멘텀(RSI, MACD)
- 수급(OBV 매집/분산, 거래량 추세)
- 변동성(ATR%, 52주 고점 대비 낙폭)
- 주요 지지/저항 레벨
- 방향성 점수(0~100) + 강세/약세 시나리오 자동 해설
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..config import TechnicalConfig
from . import technical as ta


# ----------------------------- 수급/변동성 지표 -----------------------------
def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On-Balance Volume: 상승일 거래량 누적(+), 하락일(-). 매집/분산 추적."""
    direction = np.sign(close.diff().fillna(0.0))
    return (direction * volume).cumsum()


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range: 변동성 측정."""
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat([(high - low),
                    (high - prev_close).abs(),
                    (low - prev_close).abs()], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()


def _slope_up(series: pd.Series, lookback: int = 20) -> bool:
    """최근 lookback 구간에서 우상향인지(최근값 > 과거값)."""
    s = series.dropna()
    if len(s) <= lookback:
        return False
    return bool(s.iloc[-1] > s.iloc[-lookback])


# ----------------------------- 결과 -----------------------------
@dataclass
class MarketAnalysis:
    symbol: str
    name: str
    price: float
    change_pct: float                 # 전일 대비 %
    direction_score: float            # 0~100 (방향성)
    direction_label: str
    trend: str
    momentum: str
    supply: str                       # 수급
    volatility: str
    key_levels: dict = field(default_factory=dict)
    narrative: list[str] = field(default_factory=list)
    sub_scores: dict = field(default_factory=dict)
    indicators: pd.DataFrame | None = None


def _dir_label(score: float) -> str:
    if score >= 70:
        return "강세 🟢"
    if score >= 58:
        return "강세 우위 🟢"
    if score >= 45:
        return "중립 ⚪"
    if score >= 32:
        return "약세 우위 🔴"
    return "약세 🔴"


def analyze_index(df: pd.DataFrame, cfg: TechnicalConfig, *,
                  symbol: str = "", name: str = "") -> MarketAnalysis:
    """지수 OHLCV 로 시장 국면을 종합 분석한다. (장기 데이터 권장: 2년+)"""
    ind = ta.compute_indicators(df, cfg)
    close = ind["Close"]
    ind["SMA200"] = ta.sma(close, 200)
    ind["OBV"] = obv(close, ind["Volume"])
    ind["ATR"] = atr(ind, 14)

    last = ind.iloc[-1]
    price = float(last["Close"])
    prev = float(close.iloc[-2]) if len(close) > 1 else price
    change_pct = (price / prev - 1) * 100 if prev else 0.0

    sma50 = last.get(f"SMA{cfg.sma_long}", np.nan)
    sma200 = last.get("SMA200", np.nan)
    rsi_v = last.get("RSI", np.nan)
    hist = last.get("hist", np.nan)
    obv_up = _slope_up(ind["OBV"], 20)
    vol_avg = ind["Volume"].rolling(20).mean().iloc[-1]
    vol_now = float(last["Volume"])
    atr_pct = float(last["ATR"] / price * 100) if pd.notna(last["ATR"]) else np.nan

    # 52주(252거래일) 고/저
    win = min(len(close), 252)
    high_52 = float(close.iloc[-win:].max())
    low_52 = float(close.iloc[-win:].min())
    from_high = (price / high_52 - 1) * 100 if high_52 else 0.0

    # ---- 서브 점수 (0~1) ----
    sub = {}
    sub["장기추세(200일선 위)"] = 1.0 if (pd.notna(sma200) and price > sma200) else 0.0
    sub["골든크로스(50>200)"] = 1.0 if (pd.notna(sma50) and pd.notna(sma200)
                                     and sma50 > sma200) else 0.0
    sub["MACD 모멘텀"] = 1.0 if (pd.notna(hist) and hist > 0) else 0.0
    if pd.notna(rsi_v):
        sub["RSI 건강도"] = (1.0 if 45 <= rsi_v <= 70 else
                           0.5 if (30 <= rsi_v < 45 or 70 < rsi_v <= 80) else 0.0)
    sub["수급(OBV 매집)"] = 1.0 if obv_up else 0.0
    sub["고점 대비 위치"] = (1.0 if from_high >= -5 else
                        0.5 if from_high >= -15 else 0.0)

    weights = {"장기추세(200일선 위)": .25, "골든크로스(50>200)": .20,
               "MACD 모멘텀": .15, "RSI 건강도": .15,
               "수급(OBV 매집)": .15, "고점 대비 위치": .10}
    tw = sum(weights[k] for k in sub)
    score = round(sum(sub[k] * weights[k] for k in sub) / tw * 100, 1)

    # ---- 라벨 ----
    if pd.notna(sma50) and pd.notna(sma200):
        if sma50 > sma200:
            trend = "장기 상승 추세 (골든크로스 국면)"
        else:
            trend = "장기 하락/조정 추세 (데드크로스 국면)"
        if pd.notna(sma200):
            trend += " · 현재가 200일선 " + ("위" if price > sma200 else "아래")
    else:
        trend = "추세 판단을 위한 데이터 부족"

    if pd.notna(rsi_v):
        if rsi_v > 70:
            momentum = f"과열 (RSI {rsi_v:.0f}) — 단기 조정 주의"
        elif rsi_v < 30:
            momentum = f"과매도 (RSI {rsi_v:.0f}) — 반등 가능 구간"
        else:
            momentum = f"중립~양호 (RSI {rsi_v:.0f})"
        momentum += " · MACD " + ("상승" if (pd.notna(hist) and hist > 0) else "하락")
    else:
        momentum = "데이터 부족"

    vol_ratio = (vol_now / vol_avg) if vol_avg else 1.0
    supply = ("매집 우위 (OBV 상승)" if obv_up else "분산 우위 (OBV 하락)")
    supply += (f" · 거래량 {'급증' if vol_ratio > 1.5 else '평이' if vol_ratio > 0.7 else '위축'}"
               f"(20일 평균比 {vol_ratio:.1f}배)")

    if pd.notna(atr_pct):
        vlab = ("높음" if atr_pct > 2.0 else "보통" if atr_pct > 1.0 else "낮음")
        volatility = f"{vlab} (ATR {atr_pct:.1f}%/일) · 52주 고점比 {from_high:+.1f}%"
    else:
        volatility = f"52주 고점比 {from_high:+.1f}%"

    key_levels = {
        "현재가": round(price, 2),
        "50일선": round(float(sma50), 2) if pd.notna(sma50) else None,
        "200일선": round(float(sma200), 2) if pd.notna(sma200) else None,
        "52주 고점": round(high_52, 2),
        "52주 저점": round(low_52, 2),
    }

    narrative = _build_narrative(name or symbol, price, sma50, sma200, rsi_v,
                                 hist, obv_up, from_high, high_52, low_52,
                                 atr_pct, score)

    return MarketAnalysis(
        symbol=symbol.upper(), name=name or symbol, price=price,
        change_pct=round(change_pct, 2), direction_score=score,
        direction_label=_dir_label(score), trend=trend, momentum=momentum,
        supply=supply, volatility=volatility, key_levels=key_levels,
        narrative=narrative, sub_scores={k: round(v * 100) for k, v in sub.items()},
        indicators=ind)


def _build_narrative(name, price, sma50, sma200, rsi, hist, obv_up,
                     from_high, high_52, low_52, atr_pct, score) -> list[str]:
    """지표 상태를 바탕으로 한국어 시장 해설을 생성한다."""
    n: list[str] = []

    # 추세
    if pd.notna(sma50) and pd.notna(sma200):
        if sma50 > sma200 and price > sma200:
            n.append(f"📈 **추세**: {name}는 50일선이 200일선 위에 있고 현재가도 "
                     f"200일선({sma200:,.0f}) 위 — 전형적인 **상승 추세**입니다. "
                     f"200일선이 1차 생명선 역할을 합니다.")
        elif sma50 < sma200 and price < sma200:
            n.append(f"📉 **추세**: 50일선이 200일선 아래, 현재가도 200일선"
                     f"({sma200:,.0f}) 아래 — **하락/조정 추세**입니다. "
                     f"200일선 회복 전까지는 반등을 보수적으로 보세요.")
        else:
            n.append(f"🔀 **추세**: 장·단기선이 엇갈리는 **전환 구간**입니다. "
                     f"200일선({sma200:,.0f}) 돌파/이탈 여부가 분수령입니다.")

    # 모멘텀
    if pd.notna(rsi):
        if rsi > 70:
            n.append(f"⚡ **모멘텀**: RSI {rsi:.0f} 로 **과열권**. 추세는 강하지만 "
                     f"단기 눌림이 나올 수 있어 신규 진입은 분할로.")
        elif rsi < 30:
            n.append(f"⚡ **모멘텀**: RSI {rsi:.0f} 로 **과매도**. 기술적 반등 "
                     f"가능성이 있으나 추세 확인 후 대응이 안전합니다.")
        else:
            mac = "상승" if (pd.notna(hist) and hist > 0) else "하락"
            n.append(f"⚡ **모멘텀**: RSI {rsi:.0f}(중립~양호), MACD {mac} 흐름.")

    # 수급
    n.append(f"💰 **수급**: OBV(누적 거래량)가 " +
             ("**상승 = 매집 우위**. 거래량이 가격 상승을 뒷받침합니다."
              if obv_up else
              "**하락 = 분산 우위**. 반등 시 거래량 동반 여부를 확인하세요."))

    # 변동성/위치
    if from_high <= -10:
        n.append(f"📊 **위치**: 52주 고점({high_52:,.0f}) 대비 {from_high:.1f}% "
                 f"하락 — 조정이 진행된 구간. 저점({low_52:,.0f}) 지지가 관건.")
    elif from_high >= -2:
        n.append(f"📊 **위치**: 52주 고점({high_52:,.0f}) 부근 — 신고가 도전 "
                 f"구간으로 돌파 시 추가 상승, 실패 시 차익실현 주의.")

    # 방향성 종합
    if score >= 70:
        n.append(f"🧭 **방향성(점수 {score:.0f})**: 지표 대부분이 우호적입니다. "
                 f"**추세 추종(눌림목 매수)** 전략이 유효한 국면. "
                 f"단, 200일선 이탈 시 전략 재점검.")
    elif score >= 45:
        n.append(f"🧭 **방향성(점수 {score:.0f})**: 신호가 혼재된 **중립 국면**. "
                 f"주요 레벨 돌파/이탈을 확인하며 대응하세요. 한 방향 베팅보다 "
                 f"분할·관망이 유리합니다.")
    else:
        n.append(f"🧭 **방향성(점수 {score:.0f})**: 지표가 대체로 부정적입니다. "
                 f"**리스크 관리 우선** — 반등은 추세 전환 확인 후 대응, "
                 f"현금 비중 확대도 선택지입니다.")

    return n
