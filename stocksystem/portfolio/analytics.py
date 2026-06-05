"""포트폴리오 닥터 — 보유 종목의 분산·집중도·리스크를 진단한다.

입력: {심볼: 평가금액} 딕셔너리.
출력: 비중, 섹터 분산, 집중도(HHI/최대비중), 포트폴리오 변동성, 베타(vs SPY),
종목별 변동성, 진단 코멘트와 리밸런싱 제안.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..config import Config
from ..data.base import DataProvider

TRADING_DAYS = 252
BENCHMARK = "SPY"


@dataclass
class PortfolioReport:
    weights: dict[str, float] = field(default_factory=dict)      # 심볼→비중%
    sector_weights: dict[str, float] = field(default_factory=dict)
    hhi: float = 0.0                  # 허핀달 집중도 지수(0~1)
    top_weight: float = 0.0          # 최대 단일 종목 비중%
    annual_vol: float = 0.0          # 연 변동성%
    beta: float | None = None        # vs SPY
    stock_vol: dict[str, float] = field(default_factory=dict)
    diagnosis: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    diversification_score: float = 50.0   # 0~100 (높을수록 잘 분산)


def _returns(provider, symbols, period="1y") -> pd.DataFrame:
    """심볼별 일별 수익률 DataFrame (열=심볼)."""
    cols = {}
    for s in symbols:
        try:
            df = provider.price_history(s, period=period)
            cols[s] = df["Close"].pct_change()
        except Exception:
            continue
    if not cols:
        return pd.DataFrame()
    return pd.DataFrame(cols).dropna(how="all")


def analyze_portfolio(holdings: dict[str, float], provider: DataProvider,
                      cfg: Config) -> PortfolioReport:
    """holdings = {심볼: 평가금액(USD)}."""
    holdings = {k.upper(): float(v) for k, v in holdings.items() if v > 0}
    rep = PortfolioReport()
    if not holdings:
        rep.diagnosis.append("보유 종목이 없습니다.")
        return rep

    total = sum(holdings.values())
    weights = {s: v / total for s, v in holdings.items()}
    rep.weights = {s: round(w * 100, 1) for s, w in weights.items()}

    # 집중도
    rep.hhi = round(float(sum(w ** 2 for w in weights.values())), 3)
    top_sym = max(weights, key=weights.get)
    rep.top_weight = round(weights[top_sym] * 100, 1)

    # 섹터 분산
    sectors: dict[str, float] = {}
    for s, w in weights.items():
        sec = "기타"
        try:
            sec = provider.fundamentals(s).sector or "기타"
        except Exception:
            pass
        sectors[sec] = sectors.get(sec, 0.0) + w
    rep.sector_weights = {k: round(v * 100, 1)
                          for k, v in sorted(sectors.items(),
                                             key=lambda x: -x[1])}

    # 수익률/변동성/상관/베타
    rets = _returns(provider, list(holdings) + [BENCHMARK], "1y")
    if not rets.empty:
        for s in holdings:
            if s in rets:
                rep.stock_vol[s] = round(
                    float(rets[s].std() * np.sqrt(TRADING_DAYS) * 100), 1)
        # 포트 일별 수익률 (벤치마크 제외 가중합)
        w_series = pd.Series(weights)
        avail = [s for s in holdings if s in rets]
        if avail:
            wsub = w_series[avail] / w_series[avail].sum()
            port_ret = (rets[avail] * wsub).sum(axis=1)
            rep.annual_vol = round(
                float(port_ret.std() * np.sqrt(TRADING_DAYS) * 100), 1)
            # 베타 vs SPY
            if BENCHMARK in rets:
                aligned = pd.concat([port_ret, rets[BENCHMARK]],
                                    axis=1).dropna()
                if len(aligned) > 10 and aligned.iloc[:, 1].var() > 0:
                    cov = aligned.cov().iloc[0, 1]
                    rep.beta = round(float(cov / aligned.iloc[:, 1].var()), 2)

    # 분산 점수 (집중도↓, 섹터수↑ 일수록 높음)
    n = len(holdings)
    n_sectors = len(rep.sector_weights)
    div = 100 * (1 - rep.hhi)                      # 0~100
    div = 0.6 * div + 0.4 * min(100, n_sectors / 5 * 100)
    rep.diversification_score = round(float(div), 1)

    # 진단
    if rep.top_weight > 40:
        rep.diagnosis.append(
            f"⚠️ {top_sym} 한 종목이 {rep.top_weight:.0f}%로 과도하게 집중됨")
    if n < 5:
        rep.diagnosis.append(f"⚠️ 보유 종목이 {n}개로 분산이 부족함")
    if n_sectors <= 2:
        rep.diagnosis.append(f"⚠️ 섹터가 {n_sectors}개뿐 — 업종 쏠림 위험")
    top_sec = next(iter(rep.sector_weights), None)
    if top_sec and rep.sector_weights[top_sec] > 50:
        rep.diagnosis.append(
            f"⚠️ '{top_sec}' 섹터가 {rep.sector_weights[top_sec]:.0f}%로 편중")
    if rep.beta is not None and rep.beta > 1.3:
        rep.diagnosis.append(
            f"⚠️ 베타 {rep.beta} — 시장보다 변동성이 큼(공격적)")
    if not rep.diagnosis:
        rep.diagnosis.append("✅ 큰 쏠림 없이 비교적 균형 잡힌 포트폴리오입니다.")

    # 제안
    if rep.top_weight > 40:
        rep.suggestions.append(f"{top_sym} 비중을 줄이고 다른 종목/섹터로 분산")
    if n < 5:
        rep.suggestions.append("최소 5~10종목으로 늘려 개별 종목 리스크 완화")
    if top_sec and rep.sector_weights.get(top_sec, 0) > 50:
        rep.suggestions.append(f"'{top_sec}' 외 다른 섹터(헬스케어·필수소비재 등) 편입")
    if rep.beta is not None and rep.beta > 1.3:
        rep.suggestions.append("방어주/배당주 편입으로 베타(변동성) 낮추기 고려")
    if not rep.suggestions:
        rep.suggestions.append("현재 구성을 유지하되 정기적으로 비중을 점검하세요.")

    return rep
