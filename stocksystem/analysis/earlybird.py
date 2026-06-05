"""선취매 레이더 — '남보다 먼저, 느긋하게' 후보 발굴.

대부분의 스크리너는 '이미 오른' 종목을 보여줘 늦게 사게 만든다. 이 모듈은
반대로 **아직 시장이 안 깨운, 조용히 매집되는 초기 단계** 종목을 찾는다.

선취매 점수가 높은 조건:
- 🤫 조용한 매집: OBV 상승하는데 주가는 횡보 (스마트머니 잠복 매집)
- 🌱 여유: 52주 고점 대비 적당히 눌려 있어 상승 여력이 남음
- 📈 변곡 시작: RSI 바닥권에서 반등, MACD 막 상향 전환, 이평선 회복
- 😌 낮은 변동성 + 추세 유지(200일선 위 또는 회복) → 느긋한 보유 가능
- ⛔ 이미 과열/신고가/급등은 감점 (= 이미 늦음)
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..config import TechnicalConfig
from . import technical as ta
from .market import atr, obv


@dataclass
class EarlyBirdResult:
    symbol: str
    name: str
    score: float                       # 0~100 (선취매 적합도)
    stage: str                         # 잠복/초기상승/진행중/과열/추세이탈
    reasons: list[str] = field(default_factory=list)
    accumulation: bool = False         # 조용한 매집 여부
    extended: bool = False             # 이미 많이 오름(늦음)
    metrics: dict = field(default_factory=dict)


def _stage(price, sma50, sma200, rsi, ret3m, from_high, obv_up, ret1m,
           macd_turn) -> str:
    if pd.notna(sma200) and price < sma200 * 0.95 and (
            pd.isna(sma50) or sma50 < sma200):
        return "추세이탈 🔻"
    if (pd.notna(rsi) and rsi > 70) or from_high > -3 or ret3m > 30:
        return "과열/후반 🔴"
    # 잠복: 매집 + 주가 횡보 + 이평선 근처(안 비쌈)
    if obv_up and abs(ret1m) < 6 and (pd.isna(sma50) or price <= sma50 * 1.05):
        return "잠복(조용한 매집) 🌱"
    if macd_turn or (pd.notna(rsi) and 45 <= rsi <= 62 and ret3m < 15):
        return "초기 상승(변곡) 📈"
    return "진행 중 🟡"


def analyze(df: pd.DataFrame, cfg: TechnicalConfig, *, symbol: str = "",
            name: str = "", pe: float | None = None) -> EarlyBirdResult:
    """가격/거래량(+선택 PER)으로 선취매 적합도를 점수화한다."""
    ind = ta.compute_indicators(df, cfg)
    close = ind["Close"]
    n = len(close)
    sma50 = ind[f"SMA{cfg.sma_long}"].iloc[-1]
    sma200 = ta.sma(close, 200).iloc[-1]
    rsi = ind["RSI"].iloc[-1]
    hist = ind["hist"]
    price = float(close.iloc[-1])

    ob = obv(close, ind["Volume"])
    obv_up = len(ob.dropna()) > 20 and ob.iloc[-1] > ob.iloc[-20]
    atr_pct = float(atr(ind, 14).iloc[-1] / price * 100) if n > 14 else np.nan

    ret1m = (price / float(close.iloc[-21]) - 1) * 100 if n > 21 else 0.0
    ret3m = (price / float(close.iloc[-63]) - 1) * 100 if n > 63 else 0.0
    win = min(n, 252)
    high_52 = float(close.iloc[-win:].max())
    from_high = (price / high_52 - 1) * 100 if high_52 else 0.0

    # MACD 막 상향 전환(최근 10봉 내 히스토그램 음→양)
    macd_turn = False
    h = hist.dropna()
    if len(h) > 12:
        recent = h.iloc[-10:]
        macd_turn = (recent.iloc[-1] > 0) and (recent.min() < 0)

    quiet_accum = obv_up and abs(ret1m) < 6   # 조용한 매집

    # ---------------- 점수 ----------------
    pts = 0.0
    reasons: list[str] = []

    # 1) 조용한 매집 (최대 25)
    if quiet_accum:
        pts += 25
        reasons.append("🤫 조용한 매집 — 거래량(OBV)은 느는데 주가는 횡보")
    elif obv_up:
        pts += 12
        reasons.append("매집 신호(OBV 상승)")

    # 2) 추세 유지(느긋한 보유 가능) (최대 15)
    if pd.notna(sma200):
        if price > sma200:
            pts += 13
            reasons.append("200일선 위 — 상승추세 유지(느긋이 보유 가능)")
        elif price > sma200 * 0.97:
            pts += 7
            reasons.append("200일선 회복 시도 중(추세 전환 초입)")

    # 3) 안 비쌈/안 늘어남 (최대 18)
    if pd.notna(sma50):
        if price <= sma50 * 1.05:
            pts += 12
            reasons.append("50일선 근처 — 추격 아님(좋은 진입대)")
        elif price <= sma50 * 1.12:
            pts += 4

    # 4) 상승 여력(고점 대비 눌림) (최대 12)
    if -30 <= from_high <= -10:
        pts += 12
        reasons.append(f"52주 고점比 {from_high:.0f}% — 상승 여력 충분")
    elif -45 <= from_high < -30:
        pts += 5

    # 5) 변곡(막 돌아섬) (최대 18)
    if pd.notna(rsi):
        if 45 <= rsi <= 60:
            pts += 10
            reasons.append(f"RSI {rsi:.0f} — 바닥권 반등 초기(과열 아님)")
        elif 60 < rsi <= 68:
            pts += 4
    if macd_turn:
        pts += 8
        reasons.append("MACD 막 상향 전환 — 모멘텀 초입")

    # 6) 차분함(낮은 변동성) (최대 8)
    if pd.notna(atr_pct):
        if atr_pct < 2.5:
            pts += 8
            reasons.append("변동성 낮음 — 흔들림 적어 보유 편함")
        elif atr_pct < 3.5:
            pts += 4

    # 7) 밸류에이션 (최대 8, PER 있을 때)
    if pe is not None and pe > 0:
        if pe < 22:
            pts += 8
            reasons.append(f"PER {pe:.0f} — 밸류 여유")
        elif pe > 50:
            pts -= 8
            reasons.append(f"⚠ 고PER {pe:.0f}")

    # 8) 과열/늦음 패널티
    extended = False
    if pd.notna(rsi) and rsi > 72:
        pts -= 16; extended = True
        reasons.append("⛔ RSI 과열 — 이미 늦음")
    if from_high > -3:
        pts -= 12; extended = True
        reasons.append("⛔ 신고가 부근 — 선취매 자리 아님")
    if ret3m > 35:
        pts -= 14; extended = True
        reasons.append(f"⛔ 3개월 +{ret3m:.0f}% 급등 — 이미 많이 오름")
    if pd.notna(sma50) and price > sma50 * 1.15:
        pts -= 8; extended = True
        reasons.append("⛔ 50일선보다 한참 위 — 과확장")
    # 명확한 하락추세(200일선 한참 아래)는 '느긋한 보유'에 부적합 → 감점
    if pd.notna(sma200) and price < sma200 * 0.95:
        pts -= 12
        reasons.append("⚠ 200일선 아래 하락추세 — 바닥 확인 전 진입은 위험")

    score = round(max(0.0, min(100.0, pts)), 1)
    stage = _stage(price, sma50, sma200, rsi, ret3m, from_high, obv_up,
                   ret1m, macd_turn)

    metrics = {
        "현재가": round(price, 2),
        "RSI": round(float(rsi), 1) if pd.notna(rsi) else None,
        "3개월수익": round(ret3m, 1),
        "52주고점比": round(from_high, 1),
        "변동성ATR%": round(atr_pct, 2) if pd.notna(atr_pct) else None,
        "50일선": round(float(sma50), 2) if pd.notna(sma50) else None,
        "200일선": round(float(sma200), 2) if pd.notna(sma200) else None,
    }
    return EarlyBirdResult(
        symbol=symbol.upper(), name=name or symbol, score=score, stage=stage,
        reasons=reasons, accumulation=quiet_accum, extended=extended,
        metrics=metrics)


def analyze_symbol(symbol, provider, cfg, *, period="1y") -> EarlyBirdResult:
    """공급자에서 시세(+PER)를 받아 선취매 분석."""
    from ..data.base import DataProvider  # noqa
    name, pe = symbol, None
    try:
        f = provider.fundamentals(symbol)
        name = f.name or symbol
        pe = f.trailing_pe
    except Exception:
        pass
    try:
        df = provider.price_history(symbol, period=period)
    except Exception:
        return EarlyBirdResult(symbol=symbol.upper(), name=name, score=0.0,
                               stage="데이터 없음")
    return analyze(df, cfg.technical, symbol=symbol, name=name, pe=pe)


def rank(symbols, provider, cfg, *, period="1y") -> list[EarlyBirdResult]:
    """선취매 점수 내림차순. 추세이탈/과열은 자연스럽게 하위로."""
    out = [analyze_symbol(s, provider, cfg, period=period) for s in symbols]
    out.sort(key=lambda r: r.score, reverse=True)
    return out
