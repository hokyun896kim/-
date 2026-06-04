"""종합 점수 및 매매 추천 엔진.

기술적 점수와 펀더멘털 점수를 설정 가중치로 합쳐 0~100 종합 점수를 내고,
구간에 따라 매수/보유/매도 추천을 산출한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..config import Config
from ..data.base import DataProvider, EarningsRow, UpcomingEvents
from . import fundamental as fa
from . import sentiment as se
from . import technical as ta

# 추천 라벨 (한글/영문)
RECO_LABELS = {
    "strong_buy": "적극 매수",
    "buy": "매수",
    "hold": "보유",
    "sell": "매도",
    "strong_sell": "적극 매도",
}


@dataclass
class StockAnalysis:
    symbol: str
    name: str | None
    total_score: float
    recommendation: str          # 키 (strong_buy 등)
    recommendation_label: str    # 한글 라벨
    technical: ta.TechnicalResult | None = None
    fundamental: fa.FundamentalResult | None = None
    reasons: list[str] = field(default_factory=list)
    # 부가 정보 (comprehensive 분석 시 채워짐)
    news: se.NewsSentiment | None = None
    earnings: list[EarningsRow] = field(default_factory=list)
    events: UpcomingEvents | None = None
    market_cap: float | None = None
    sector: str | None = None

    def summary_row(self) -> dict:
        """대시보드 표용 한 줄 요약."""
        tech = self.technical.score if self.technical else None
        fund = self.fundamental.score if self.fundamental else None
        price = (self.technical.latest.get("close")
                 if self.technical else None)
        row = {
            "종목": self.symbol,
            "이름": self.name,
            "현재가": round(price, 2) if price else None,
            "종합점수": self.total_score,
            "기술점수": tech,
            "펀더멘털점수": fund,
            "추천": self.recommendation_label,
        }
        if self.news is not None:
            row["뉴스분위기"] = self.news.score
        return row


def _classify(score: float, cfg: Config) -> str:
    r = cfg.recommendation
    if score >= r.strong_buy:
        return "strong_buy"
    if score >= r.buy:
        return "buy"
    if score >= r.hold:
        return "hold"
    if score >= r.sell:
        return "sell"
    return "strong_sell"


def _build_reasons(tech: ta.TechnicalResult | None,
                   fund: fa.FundamentalResult | None) -> list[str]:
    reasons: list[str] = []
    if tech:
        buys = [k for k, v in tech.signals.items() if v == "buy"]
        sells = [k for k, v in tech.signals.items() if v == "sell"]
        if buys:
            reasons.append("기술적 매수 신호: " + ", ".join(buys))
        if sells:
            reasons.append("기술적 매도 신호: " + ", ".join(sells))
    if fund:
        top = sorted(fund.metric_scores.items(), key=lambda x: x[1], reverse=True)
        if top and top[0][1] >= 70:
            reasons.append(f"펀더멘털 강점: {top[0][0]}({top[0][1]:.0f}점)")
        if top and top[-1][1] <= 35:
            reasons.append(f"펀더멘털 약점: {top[-1][0]}({top[-1][1]:.0f}점)")
        reasons.extend(fund.notes)
    return reasons


def analyze_symbol(symbol: str, provider: DataProvider, cfg: Config,
                   period: str = "1y") -> StockAnalysis:
    """한 종목에 대해 기술적+기본적 분석을 모두 수행하고 종합한다."""
    tech_res = None
    fund_res = None
    name = symbol

    # 기술적 분석
    try:
        df = provider.price_history(symbol, period=period)
        tech_res = ta.analyze(df, cfg.technical, symbol=symbol)
    except Exception as e:  # 데이터 실패 시에도 펀더멘털만으로 진행
        pass

    # 기본적 분석
    sector = None
    market_cap = None
    try:
        f = provider.fundamentals(symbol)
        name = f.name or symbol
        sector = f.sector
        market_cap = f.market_cap
        fund_res = fa.analyze(f)
    except Exception:
        pass

    # 종합 점수 (가용한 쪽만 있으면 그쪽 100%)
    wt, wf = cfg.weights.technical, cfg.weights.fundamental
    if tech_res and fund_res:
        total = (tech_res.score * wt + fund_res.score * wf) / (wt + wf)
    elif tech_res:
        total = tech_res.score
    elif fund_res:
        total = fund_res.score
    else:
        total = 50.0
    total = round(total, 1)

    reco = _classify(total, cfg)
    return StockAnalysis(
        symbol=symbol.upper(),
        name=name,
        total_score=total,
        recommendation=reco,
        recommendation_label=RECO_LABELS[reco],
        technical=tech_res,
        fundamental=fund_res,
        reasons=_build_reasons(tech_res, fund_res),
        market_cap=market_cap,
        sector=sector,
    )


def analyze_full(symbol: str, provider: DataProvider, cfg: Config,
                 period: str = "1y") -> StockAnalysis:
    """종목 상세용 종합 분석: 기술/펀더멘털 + 뉴스 분위기 + 실적 + 이벤트.

    네트워크 비용이 더 들기 때문에 '종목 상세' 화면에서만 사용한다.
    """
    res = analyze_symbol(symbol, provider, cfg, period)
    try:
        res.news = se.aggregate(provider.news(symbol))
    except Exception:
        res.news = se.aggregate([])
    try:
        res.earnings = provider.earnings_history(symbol)
    except Exception:
        res.earnings = []
    try:
        res.events = provider.events(symbol)
    except Exception:
        res.events = UpcomingEvents(symbol=symbol.upper())

    # 뉴스 분위기를 판단 근거에 반영
    if res.news and res.news.n_articles:
        if res.news.score >= 60:
            res.reasons.append(f"최근 뉴스 분위기 우호적 ({res.news.label})")
        elif res.news.score <= 40:
            res.reasons.append(f"최근 뉴스 분위기 부정적 ({res.news.label})")
    return res


def analyze_watchlist(symbols: list[str], provider: DataProvider,
                      cfg: Config, period: str = "1y") -> list[StockAnalysis]:
    """관심종목 전체를 분석하고 종합점수 내림차순으로 정렬해 반환."""
    results = [analyze_symbol(s, provider, cfg, period) for s in symbols]
    results.sort(key=lambda r: r.total_score, reverse=True)
    return results
