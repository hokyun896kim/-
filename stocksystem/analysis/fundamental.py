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
    sector_neutral: bool = False                   # 섹터 상대평가 적용 여부


# 섹터에 따라 정상 범위가 크게 다른 지표들.
#
# 절대 구간으로 채점하면 은행(PER 13)·통신(PER 10)이 자동으로 고득점하고
# 반도체·소프트웨어(PER 35+)는 자동으로 감점된다. 실제로 이 시스템은
# NVDA(65.0)보다 VZ형 통신주(71.0)를, MSFT(65.6)보다 JPM형 은행(76.5)을
# 높게 매겼다. 의도한 밸류 팩터 베팅이 아니라 채점표의 부작용이다.
# sector_neutral=True 면 같은 섹터 안에서의 백분위로 바꿔 이 편향을 없앤다.
SECTOR_RELATIVE_METRICS = ("PER", "PBR", "부채비율")

# 값이 낮을수록 좋은 지표 (백분위를 뒤집어야 한다)
_LOWER_IS_BETTER = {"PER", "PBR", "부채비율"}

_METRIC_ATTR = {
    "PER": "trailing_pe",
    "PBR": "price_to_book",
    "부채비율": "debt_to_equity",
}


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


# --------------------------- 섹터 상대평가 ---------------------------
def _percentile_scores(values: dict[str, float], lower_is_better: bool
                       ) -> dict[str, float]:
    """같은 섹터 안에서의 백분위를 0~100 점으로 환산한다.

    동점은 평균 순위를 준다. 표본이 1개면 중립(50)으로 둔다.
    """
    n = len(values)
    if n == 0:
        return {}
    if n == 1:
        return {k: 50.0 for k in values}
    items = sorted(values.items(), key=lambda kv: kv[1])
    # 동점 처리: 같은 값끼리 평균 순위
    ranks: dict[str, float] = {}
    i = 0
    while i < n:
        j = i
        while j + 1 < n and items[j + 1][1] == items[i][1]:
            j += 1
        avg_rank = (i + j) / 2.0
        for k in range(i, j + 1):
            ranks[items[k][0]] = avg_rank
        i = j + 1
    out = {}
    for sym, r in ranks.items():
        pct = r / (n - 1)                    # 0(최저) ~ 1(최고)
        out[sym] = round((1 - pct if lower_is_better else pct) * 100, 1)
    return out


def analyze_cross_section(items: list[Fundamentals], *,
                          sector_neutral: bool = True,
                          min_peers: int = 4) -> list[FundamentalResult]:
    """여러 종목을 함께 채점한다. 밸류에이션 지표는 섹터 상대평가로.

    sector_neutral=False 면 기존 analyze() 를 종목별로 부른 것과 동일하다.
    한 섹터의 유효 표본이 min_peers 미만이면 그 섹터는 절대 구간으로 폴백한다
    (표본 3개짜리 백분위는 신뢰할 수 없다).
    """
    results = [analyze(f) for f in items]
    if not sector_neutral or len(items) < min_peers:
        return results

    by_symbol = {r.symbol: r for r in results}
    fund_by_symbol = {f.symbol: f for f in items}

    # 섹터별로 묶는다 (섹터 미상은 상대평가 대상에서 제외)
    sectors: dict[str, list[str]] = {}
    for f in items:
        if f.sector:
            sectors.setdefault(f.sector, []).append(f.symbol)

    for metric in SECTOR_RELATIVE_METRICS:
        attr = _METRIC_ATTR[metric]
        for sector, syms in sectors.items():
            # 양수 값만 상대평가한다. 적자(PER<=0)를 '가장 싸다'로 랭킹하면
            # 정반대 결론이 나오므로 절대 채점의 페널티를 그대로 유지한다.
            vals = {}
            for s in syms:
                v = getattr(fund_by_symbol[s], attr, None)
                if v is not None and v > 0:
                    vals[s] = float(v)
            if len(vals) < min_peers:
                continue                      # 표본 부족 → 절대 구간 유지
            pct = _percentile_scores(vals, metric in _LOWER_IS_BETTER)
            for s, sc in pct.items():
                if metric in by_symbol[s].metric_scores:
                    by_symbol[s].metric_scores[metric] = sc

    # 바뀐 지표 점수로 종합점수 재계산
    for r in results:
        ms = r.metric_scores
        if ms:
            tw = sum(_WEIGHTS[k] for k in ms)
            r.score = round(sum(ms[k] * _WEIGHTS[k] for k in ms) / tw, 1)
        r.sector_neutral = True
    return results
