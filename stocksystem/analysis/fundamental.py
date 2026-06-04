"""기본적 분석 모듈.

재무 지표(PER, PBR, ROE, 성장률, 배당 등)를 각각 0~100 점으로 환산해
종합 펀더멘털 점수를 만든다. 값이 없는 지표는 점수 계산에서 제외한다.

채점 철학(중급자 기준):
- 밸류에이션(PER/PBR)은 낮을수록 가점 (단, 음수/과도하게 낮으면 감점)
- 수익성(ROE/순이익률)은 높을수록 가점
- 성장성(매출/이익 성장)은 높을수록 가점
- 재무건전성(부채비율)은 낮을수록 가점
- 배당은 보너스 성격으로 소폭 반영
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..data.base import Fundamentals


def _band_score(value, bands) -> float:
    """구간(bands)에 따라 점수를 매긴다.

    bands: [(threshold, score), ...] threshold 오름차순.
    value 가 threshold 이하인 첫 구간의 score 를 반환.
    마지막 구간은 (inf, score) 로 끝낸다.
    """
    for threshold, score in bands:
        if value <= threshold:
            return score
    return bands[-1][1]


def score_pe(pe) -> float | None:
    if pe is None:
        return None
    if pe <= 0:          # 적자 → 밸류에이션 의미 약함, 낮은 점수
        return 25.0
    return _band_score(pe, [(10, 95), (15, 85), (20, 70),
                            (25, 55), (35, 40), (50, 25), (float("inf"), 10)])


def score_pb(pb) -> float | None:
    if pb is None:
        return None
    if pb <= 0:
        return 30.0
    return _band_score(pb, [(1, 95), (2, 85), (3, 72), (5, 58),
                            (8, 42), (12, 28), (float("inf"), 15)])


def score_roe(roe) -> float | None:
    if roe is None:
        return None
    # roe 는 소수(0.25 = 25%)
    return _band_score(roe, [(0.0, 15), (0.05, 35), (0.10, 50),
                             (0.15, 65), (0.20, 78), (0.30, 90),
                             (float("inf"), 95)])


def score_margin(m) -> float | None:
    if m is None:
        return None
    return _band_score(m, [(0.0, 15), (0.05, 40), (0.10, 55),
                           (0.20, 72), (0.30, 88), (float("inf"), 95)])


def score_growth(g) -> float | None:
    if g is None:
        return None
    return _band_score(g, [(-0.10, 10), (0.0, 30), (0.05, 50),
                           (0.15, 70), (0.30, 88), (float("inf"), 95)])


def score_debt(de) -> float | None:
    """부채비율(%). 낮을수록 좋음."""
    if de is None:
        return None
    return _band_score(de, [(30, 95), (60, 82), (100, 65),
                            (150, 48), (200, 32), (float("inf"), 18)])


def score_dividend(dy) -> float | None:
    if dy is None:
        return None
    # 배당수익률 소수. 보너스 성격이라 범위를 좁게.
    return _band_score(dy, [(0.0, 50), (0.01, 60), (0.02, 70),
                            (0.04, 85), (float("inf"), 90)])


# 지표별 가중치 (합 = 1.0). 배당은 보너스라 작게.
_WEIGHTS = {
    "PER": 0.20,
    "PBR": 0.15,
    "ROE": 0.20,
    "순이익률": 0.15,
    "매출성장": 0.12,
    "이익성장": 0.10,
    "부채비율": 0.05,
    "배당": 0.03,
}


@dataclass
class FundamentalResult:
    symbol: str
    score: float                                   # 0~100
    metric_scores: dict[str, float] = field(default_factory=dict)
    fundamentals: Fundamentals | None = None
    notes: list[str] = field(default_factory=list)


def analyze(f: Fundamentals) -> FundamentalResult:
    raw = {
        "PER": score_pe(f.trailing_pe),
        "PBR": score_pb(f.price_to_book),
        "ROE": score_roe(f.return_on_equity),
        "순이익률": score_margin(f.profit_margin),
        "매출성장": score_growth(f.revenue_growth),
        "이익성장": score_growth(f.earnings_growth),
        "부채비율": score_debt(f.debt_to_equity),
        "배당": score_dividend(f.dividend_yield),
    }
    metric_scores = {k: v for k, v in raw.items() if v is not None}

    # 사용 가능한 지표만으로 가중평균 (가중치 재정규화)
    if metric_scores:
        total_w = sum(_WEIGHTS[k] for k in metric_scores)
        score = sum(metric_scores[k] * _WEIGHTS[k] for k in metric_scores) / total_w
        score = round(score, 1)
    else:
        score = 50.0  # 데이터 없음 → 중립

    notes = []
    if f.trailing_pe is not None and f.trailing_pe <= 0:
        notes.append("적자 상태(PER 음수) — 밸류에이션 해석에 주의")
    if f.revenue_growth is not None and f.revenue_growth < 0:
        notes.append("매출 역성장 중")
    if f.debt_to_equity is not None and f.debt_to_equity > 150:
        notes.append("부채비율이 높음")
    if len(metric_scores) < 4:
        notes.append("재무 데이터가 부족해 점수 신뢰도가 낮음")

    return FundamentalResult(symbol=f.symbol, score=score,
                             metric_scores=metric_scores,
                             fundamentals=f, notes=notes)
