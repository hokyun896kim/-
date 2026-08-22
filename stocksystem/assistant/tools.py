"""비서가 호출하는 도구(tool) 계층.

비서는 숫자를 **직접 만들어내지 않는다**. 질문을 받으면 여기 정의된 도구 중
하나를 골라 기존 분석 모듈(technical/fundamental/scoring/market/...)을 그대로
실행하고, 그 결과만 말로 옮긴다. 그래서 대시보드·CLI·비서가 같은 숫자를 낸다.

각 도구는 세 가지를 갖는다.
  - schema : Claude API 에 넘길 JSON Schema (LLM 이 인자를 채운다)
  - run    : 실제 실행 함수 → JSON 직렬화 가능한 dict
  - render : dict → 사람이 읽을 한국어 텍스트 (규칙 기반 엔진과 CLI 가 사용)

run() 의 반환 dict 는 그대로 tool_result 로 모델에 들어가므로, 원본
dataclass 를 넘기지 말고 필요한 필드만 추려 담는다(토큰·직렬화 양쪽 문제).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable

from ..config import Config
from ..data import get_provider
from ..data.base import DataProvider
from ..data.universe import filter_universe, load_universe, sectors
from ..analysis import earlybird as eb
from ..analysis import factors as fct
from ..analysis import hegemony as hg
from ..analysis import market as mk
from ..analysis import montecarlo as mcarlo
from ..analysis import sentiment as se
from ..analysis.scoring import (analyze_full, analyze_symbol,
                                apply_sector_neutral)
from ..backtest import STRATEGIES, backtest_symbol
from ..portfolio.analytics import analyze_portfolio
from ..portfolio.paper_broker import (DEFAULT_STATE, InsufficientFundsError,
                                      InsufficientSharesError, PaperBroker)

# 스크리너/레이더가 한 번에 훑는 종목 수 상한.
#
# yfinance 는 종목당 시세+재무 2회를 부르므로 유니버스(125종목)를 다 돌면
# 250여 건이 나가고 몇 분이 걸린다. 대화형 비서에서 그건 사실상 멈춘 것과
# 같아서, 시총 상위부터 이 개수까지만 본다. 잘린 사실은 결과에 남긴다.
MAX_SCAN = 40


# ----------------------------- 심볼 해석 -----------------------------

# 한글로 부르는 이름 → 티커. 유니버스 CSV 는 영문명만 갖고 있어서,
# "엔비디아 어때?" 같은 질문을 받으려면 이 표가 필요하다.
KOREAN_ALIASES = {
    "애플": "AAPL", "마이크로소프트": "MSFT", "엠에스": "MSFT",
    "마소": "MSFT", "마이크로": "MSFT",
    "엔비디아": "NVDA", "구글": "GOOGL", "알파벳": "GOOGL",
    "아마존": "AMZN", "메타": "META", "페이스북": "META",
    "테슬라": "TSLA", "넷플릭스": "NFLX", "브로드컴": "AVGO",
    "구글알파벳": "GOOGL", "아마존닷컴": "AMZN",
    "인텔": "INTC", "amd": "AMD", "에이엠디": "AMD",
    "퀄컴": "QCOM", "마이크론": "MU", "티에스엠씨": "TSM", "티에스엠": "TSM",
    "오라클": "ORCL", "세일즈포스": "CRM", "어도비": "ADBE",
    "팔란티어": "PLTR", "우버": "UBER", "코스트코": "COST",
    "월마트": "WMT", "존슨앤존슨": "JNJ", "일라이릴리": "LLY", "릴리": "LLY",
    "화이자": "PFE", "머크": "MRK", "애브비": "ABBV",
    "제이피모건": "JPM", "제피모건": "JPM", "뱅크오브아메리카": "BAC",
    "비자": "V", "마스터카드": "MA", "버크셔": "BRK-B",
    "코카콜라": "KO", "펩시": "PEP", "맥도날드": "MCD", "나이키": "NKE",
    "스타벅스": "SBUX", "디즈니": "DIS", "보잉": "BA",
    "엑슨": "XOM", "엑슨모빌": "XOM", "쉐브론": "CVX",
    "S&P": "SPY", "에스앤피": "SPY", "스앤피": "SPY", "나스닥": "QQQ",
    "다우": "DIA", "다우존스": "DIA", "빅스": "^VIX",
}


def resolve_symbol(text: str) -> str | None:
    """사람이 쓴 표현에서 티커를 뽑는다. 못 찾으면 None.

    우선순위: 한글 별칭 → 유니버스 티커 정확일치 → 영문 회사명 부분일치.
    """
    if not text:
        return None
    raw = text.strip()
    low = raw.lower()

    for ko, sym in KOREAN_ALIASES.items():
        if ko.lower() in low:
            return sym

    upper = raw.upper()
    known = {u.symbol for u in load_universe()}
    if upper in known:
        return upper

    for u in load_universe():
        # "Apple Inc." → "apple" 로 잘라 비교 (법인격 접미어 제거)
        head = u.name.lower().split(" inc")[0].split(" corp")[0].strip(" .,")
        if head and head in low:
            return u.symbol
    return None


# ----------------------------- 실행 컨텍스트 -----------------------------


@dataclass
class AssistantContext:
    """도구들이 공유하는 실행 환경 (설정·데이터 공급자·모의계좌)."""

    cfg: Config
    provider_name: str = "yahoo"
    _provider: DataProvider | None = None
    broker_state: str = str(DEFAULT_STATE)

    @property
    def provider(self) -> DataProvider:
        if self._provider is None:
            self._provider = get_provider(self.provider_name)
        return self._provider

    def load_broker(self) -> PaperBroker:
        return PaperBroker.load(
            self.broker_state,
            initial_cash=self.cfg.paper_trading.initial_cash,
            commission=self.cfg.paper_trading.commission,
        )

    def price_of(self, symbol: str) -> float | None:
        try:
            df = self.provider.price_history(symbol, period="1mo")
            return float(df["Close"].iloc[-1])
        except Exception:
            return None


# ----------------------------- 직렬화 유틸 -----------------------------


def _clean(obj: Any) -> Any:
    """numpy/pandas 스칼라와 NaN 을 순수 JSON 값으로 바꾼다.

    NaN 은 json.dumps 가 `NaN` 으로 뱉는데 이건 표준 JSON 이 아니라서
    모델 쪽에서 깨진다. 값이 없다는 뜻이므로 None 으로 통일한다.
    """
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if hasattr(obj, "item") and not isinstance(obj, (str, bytes)):
        try:                       # numpy 스칼라
            return _clean(obj.item())
        except Exception:
            pass
    if isinstance(obj, (int, float, str, bool)) or obj is None:
        return obj
    return str(obj)


def _r(v, nd: int = 2):
    """None 안전 반올림."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else round(f, nd)


def _pct(v, nd: int = 1) -> str:
    return "—" if v is None else f"{v:+.{nd}f}%"


# 모든 도구 결과에 붙는 꼬리말. 등급을 매매 지시로 읽지 않게 한다.
SCORE_CAVEAT = ("종합점수는 이벤트 스터디에서 미래 수익률 예측력이 확인되지 "
                "않았습니다(IC −0.016). 등급은 점수 구간에서의 위치일 뿐 "
                "매매 신호가 아닙니다.")


# ----------------------------- 도구 구현 -----------------------------


def _tool_analyze_stock(ctx: AssistantContext, symbol: str,
                        period: str = "1y") -> dict:
    sym = resolve_symbol(symbol) or symbol.upper()
    res = analyze_full(sym, ctx.provider, ctx.cfg, period)
    tech, fund = res.technical, res.fundamental
    out: dict[str, Any] = {
        "symbol": res.symbol,
        "name": res.name,
        "sector": res.sector,
        "price": _r(tech.latest.get("close")) if tech else None,
        "total_score": res.total_score,
        "grade": res.recommendation_label,
        "technical_score": _r(tech.score, 1) if tech else None,
        "fundamental_score": _r(fund.score, 1) if fund else None,
        "signals": dict(tech.signals) if tech else {},
        "indicators": {k: _r(v) for k, v in tech.latest.items()} if tech else {},
        "reasons": list(res.reasons),
        "caveat": SCORE_CAVEAT,
    }
    if fund:
        out["metric_scores"] = {k: _r(v, 1) for k, v in fund.metric_scores.items()}
    if res.news:
        out["news"] = {"score": _r(res.news.score, 1), "label": res.news.label,
                       "n_articles": res.news.n_articles,
                       "confidence": res.news.confidence}
    if res.events:
        out["events"] = {"next_earnings": res.events.next_earnings_date,
                         "ex_dividend": res.events.ex_dividend_date,
                         "dividend": _r(res.events.dividend_amount)}
    if res.earnings:
        out["recent_earnings"] = [
            {"period": e.period, "eps_actual": _r(e.eps_actual),
             "eps_estimate": _r(e.eps_estimate), "surprise_pct": _r(e.surprise_pct, 1)}
            for e in res.earnings[:4]
        ]
    return _clean(out)


def _render_analyze_stock(d: dict) -> str:
    if d.get("error"):
        return f"❌ {d['error']}"
    lines = [f"**{d['symbol']} {d.get('name') or ''}** — 종합 {d['total_score']}점 "
             f"({d['grade']})"]
    if d.get("price"):
        lines.append(f"- 현재가 ${d['price']:,.2f} · 섹터 {d.get('sector') or '—'}")
    lines.append(f"- 기술 {d.get('technical_score') or '—'} / "
                 f"펀더멘털 {d.get('fundamental_score') or '—'}")
    if d.get("signals"):
        sig = " · ".join(f"{k}:{v}" for k, v in d["signals"].items())
        lines.append(f"- 신호: {sig}")
    if d.get("news"):
        n = d["news"]
        lines.append(f"- 뉴스 분위기: {n['label']} ({n['score']}/100, "
                     f"{n['n_articles']}건)")
    ev = d.get("events") or {}
    if ev.get("next_earnings"):
        lines.append(f"- 다음 실적: {ev['next_earnings']}")
    for r in d.get("reasons", [])[:5]:
        lines.append(f"  • {r}")
    lines.append(f"\n> ⚠️ {d['caveat']}")
    return "\n".join(lines)


def _tool_market_overview(ctx: AssistantContext) -> dict:
    indices = []
    for sym, name in (("SPY", "S&P 500"), ("QQQ", "나스닥 100"),
                      ("DIA", "다우존스")):
        try:
            df = ctx.provider.price_history(sym, period="2y")
            m = mk.analyze_index(df, ctx.cfg.technical, symbol=sym, name=name)
            indices.append({
                "symbol": sym, "name": name, "price": _r(m.price),
                "change_pct": _r(m.change_pct),
                "direction_score": _r(m.direction_score, 0),
                "direction_label": m.direction_label,
                "trend": m.trend, "momentum": m.momentum,
                "supply": m.supply, "volatility": m.volatility,
                "narrative": list(m.narrative)[:4],
            })
        except Exception as e:
            indices.append({"symbol": sym, "name": name, "error": str(e)})

    out: dict[str, Any] = {"indices": indices}
    try:
        fg = mk.fear_greed(ctx.provider, ctx.cfg.technical)
        out["fear_greed"] = {"score": _r(fg.score, 0), "label": fg.label,
                             "components": {k: _r(v, 0)
                                            for k, v in fg.components.items()}}
    except Exception:
        pass
    vix = ctx.price_of("^VIX")
    if vix:
        out["vix"] = _r(vix)
    return _clean(out)


def _render_market_overview(d: dict) -> str:
    if d.get("error"):
        return f"❌ {d['error']}"
    lines = ["**시장 개요**"]
    for ix in d.get("indices", []):
        if ix.get("error"):
            lines.append(f"- {ix['name']}: 데이터 조회 실패")
            continue
        lines.append(f"- {ix['name']} ${ix['price']:,.2f} "
                     f"({_pct(ix['change_pct'], 2)}) · 방향성 "
                     f"{ix['direction_score']:.0f} {ix['direction_label']}")
    if d.get("fear_greed"):
        fg = d["fear_greed"]
        lines.append(f"- 공포·탐욕 지수: {fg['score']:.0f} {fg['label']}")
    if d.get("vix"):
        lines.append(f"- VIX: {d['vix']}")
    first = next((i for i in d.get("indices", []) if not i.get("error")), None)
    if first and first.get("narrative"):
        lines.append("\n진단:")
        for n in first["narrative"]:
            lines.append(f"  • {n}")
    lines.append("\n> ⚠️ 지표 기반 자동 해설이며 예측이 아닙니다.")
    return "\n".join(lines)


def _scan_symbols(top_pct: float, sector: str | None) -> tuple[list[str], int]:
    """스캔 대상 티커와 (상한에 걸려) 잘린 개수를 돌려준다."""
    uni = filter_universe(top_pct=top_pct, sector=sector)
    syms = [u.symbol for u in uni]
    return syms[:MAX_SCAN], max(0, len(syms) - MAX_SCAN)


def _tool_screen_stocks(ctx: AssistantContext, top_pct: float = 30.0,
                        sector: str | None = None, limit: int = 10,
                        period: str = "1y") -> dict:
    syms, skipped = _scan_symbols(top_pct, sector)
    if not syms:
        return {"error": f"조건에 맞는 종목이 없습니다 (섹터={sector})",
                "available_sectors": sectors()}
    results = [analyze_symbol(s, ctx.provider, ctx.cfg, period) for s in syms]
    apply_sector_neutral(results, ctx.cfg)
    results.sort(key=lambda r: r.total_score, reverse=True)
    return _clean({
        "criteria": {"top_pct": top_pct, "sector": sector or "전체",
                     "scanned": len(syms), "skipped_over_limit": skipped},
        "ranking": [
            {"rank": i, "symbol": r.symbol, "name": r.name,
             "total_score": r.total_score, "grade": r.recommendation_label,
             "technical_score": _r(r.technical.score, 1) if r.technical else None,
             "fundamental_score": _r(r.fundamental.score, 1) if r.fundamental else None,
             "sector": r.sector}
            for i, r in enumerate(results[:max(1, int(limit))], 1)
        ],
        "caveat": SCORE_CAVEAT,
    })


def _render_screen_stocks(d: dict) -> str:
    if d.get("error"):
        return (f"❌ {d['error']}\n사용 가능한 섹터: "
                f"{', '.join(d.get('available_sectors', []))}")
    c = d["criteria"]
    lines = [f"**스크리너** — 시총 상위 {c['top_pct']:g}% · 섹터 {c['sector']} "
             f"· {c['scanned']}종목 스캔"]
    if c.get("skipped_over_limit"):
        lines.append(f"_(시총 상위 {MAX_SCAN}종목만 봤습니다 — "
                     f"{c['skipped_over_limit']}종목 제외)_")
    for r in d["ranking"]:
        lines.append(f"{r['rank']:>2}. {r['symbol']:<6} {r['total_score']:>5.1f}점 "
                     f"({r['grade']}) · 기술 {r.get('technical_score') or '—'} "
                     f"/ 펀더 {r.get('fundamental_score') or '—'}")
    lines.append(f"\n> ⚠️ {d['caveat']}")
    return "\n".join(lines)


def _tool_early_bird(ctx: AssistantContext, sector: str | None = None,
                     limit: int = 8) -> dict:
    syms, skipped = _scan_symbols(50.0, sector)
    if not syms:
        return {"error": f"조건에 맞는 종목이 없습니다 (섹터={sector})",
                "available_sectors": sectors()}
    ranked = eb.rank(syms, ctx.provider, ctx.cfg)
    return _clean({
        "criteria": {"sector": sector or "전체", "scanned": len(syms),
                     "skipped_over_limit": skipped},
        "ranking": [
            {"rank": i, "symbol": r.symbol, "name": r.name,
             "score": _r(r.score, 1), "stage": r.stage,
             "accumulation": r.accumulation, "extended": r.extended,
             "reasons": list(r.reasons)[:3]}
            for i, r in enumerate(ranked[:max(1, int(limit))], 1)
        ],
        "caveat": "선취매 점수는 '아직 안 오른 매집 구간'을 찾는 탐색 도구입니다. "
                  "상승을 보장하지 않습니다.",
    })


def _render_early_bird(d: dict) -> str:
    if d.get("error"):
        return f"❌ {d['error']}"
    c = d["criteria"]
    lines = [f"**선취매 레이더** — 섹터 {c['sector']} · {c['scanned']}종목 스캔"]
    for r in d["ranking"]:
        tag = " 🤫매집" if r["accumulation"] else (" ⚠️과열" if r["extended"] else "")
        lines.append(f"{r['rank']:>2}. {r['symbol']:<6} {r['score']:>5.1f}점 · "
                     f"{r['stage']}{tag}")
        for why in r["reasons"]:
            lines.append(f"      · {why}")
    lines.append(f"\n> ⚠️ {d['caveat']}")
    return "\n".join(lines)


def _tool_hegemony(ctx: AssistantContext, symbols: list[str]) -> dict:
    syms = [resolve_symbol(s) or s.upper() for s in symbols][:12]
    ranked = hg.rank(syms, ctx.provider)
    return _clean({
        "results": [
            {"symbol": r.symbol, "verdict": r.verdict,
             "annual_rev_yoy": r.annual_rev_yoy, "annual_op_yoy": r.annual_op_yoy,
             "annual_spread": r.annual_spread, "ttm_spread": r.ttm_spread,
             "accel": r.accel, "quality": r.quality, "reliable": r.reliable,
             "note": r.note}
            for r in ranked
        ],
        "caveat": "스프레드는 영업이익YoY − 매출YoY 입니다. 기저효과(전년 적자·"
                  "급락)면 신뢰도가 낮습니다.",
    })


def _render_hegemony(d: dict) -> str:
    if d.get("error"):
        return f"❌ {d['error']}"
    lines = ["**헤게모니 스프레드** (영업이익YoY − 매출YoY)"]
    for r in d.get("results", []):
        if r["annual_spread"] is None:
            lines.append(f"- {r['symbol']}: 데이터 부족")
            continue
        lines.append(
            f"- {r['symbol']:<6} 연간 스프레드 {r['annual_spread']:+.1f}%p "
            f"(매출 {_pct(r['annual_rev_yoy'])} / 영익 {_pct(r['annual_op_yoy'])})"
            f" · TTM {_pct(r['ttm_spread'])}p · {r['verdict']}")
        if r.get("note"):
            lines.append(f"      · {r['note']}")
    lines.append(f"\n> ⚠️ {d['caveat']}")
    return "\n".join(lines)


def _tool_compare_stocks(ctx: AssistantContext, symbols: list[str]) -> dict:
    syms = [resolve_symbol(s) or s.upper() for s in symbols][:6]
    if len(syms) < 2:
        return {"error": "비교하려면 종목이 2개 이상 필요합니다."}
    profiles = fct.compare(syms, ctx.provider, ctx.cfg)
    return _clean({
        "profiles": [{"symbol": p.symbol, "name": p.name,
                      "overall": p.overall, "factors": p.scores}
                     for p in profiles],
        "caveat": "5팩터 점수는 상대 비교용 프로파일이며 수익률 예측이 아닙니다.",
    })


def _render_compare_stocks(d: dict) -> str:
    if d.get("error"):
        return f"❌ {d['error']}"
    profs = d["profiles"]
    keys = list(profs[0]["factors"].keys())
    head = "종목    " + "".join(f"{k:>7}" for k in keys) + "   종합"
    lines = ["**팩터 비교**", "```", head, "─" * len(head)]
    for p in profs:
        row = f"{p['symbol']:<7}" + "".join(
            f"{p['factors'][k]:>7.1f}" for k in keys)
        lines.append(f"{row}{p['overall']:>7.1f}")
    lines.append("```")
    lines.append(f"> ⚠️ {d['caveat']}")
    return "\n".join(lines)


def _tool_portfolio_checkup(ctx: AssistantContext,
                            holdings: list[dict]) -> dict:
    parsed: dict[str, float] = {}
    for h in holdings or []:
        sym = resolve_symbol(str(h.get("symbol", ""))) or str(
            h.get("symbol", "")).upper()
        try:
            val = float(h.get("value", 0))
        except (TypeError, ValueError):
            val = 0.0
        if sym and val > 0:
            parsed[sym] = parsed.get(sym, 0.0) + val
    if not parsed:
        return {"error": "보유 종목과 평가금액(USD)이 필요합니다. "
                         "예: AAPL 5000달러, MSFT 3000달러"}
    rep = analyze_portfolio(parsed, ctx.provider, ctx.cfg)
    return _clean({
        "holdings": parsed,
        "weights": rep.weights,
        "sector_weights": rep.sector_weights,
        "hhi": _r(rep.hhi, 3),
        "top_weight": _r(rep.top_weight, 1),
        "annual_vol": _r(rep.annual_vol, 1),
        "beta": _r(rep.beta, 2),
        "diversification_score": _r(rep.diversification_score, 1),
        "diagnosis": list(rep.diagnosis),
        "suggestions": list(rep.suggestions),
    })


def _render_portfolio_checkup(d: dict) -> str:
    if d.get("error"):
        return f"❌ {d['error']}"
    lines = [f"**포트폴리오 진단** — 분산 점수 {d['diversification_score']}/100"]
    lines.append(f"- 연 변동성 {d['annual_vol']}% · 베타 {d.get('beta') or '—'} "
                 f"· 최대 단일 비중 {d['top_weight']}%")
    w = ", ".join(f"{k} {v}%" for k, v in (d.get("weights") or {}).items())
    lines.append(f"- 비중: {w}")
    if d.get("sector_weights"):
        s = ", ".join(f"{k} {v}%" for k, v in d["sector_weights"].items())
        lines.append(f"- 섹터: {s}")
    for x in d.get("diagnosis", []):
        lines.append(f"  • {x}")
    if d.get("suggestions"):
        lines.append("제안:")
        for x in d["suggestions"]:
            lines.append(f"  → {x}")
    return "\n".join(lines)


def _tool_backtest(ctx: AssistantContext, symbol: str, strategy: str,
                   period: str = "2y") -> dict:
    sym = resolve_symbol(symbol) or symbol.upper()
    if strategy not in STRATEGIES:
        # 부분 일치 허용 ("RSI" → "RSI 역추세")
        cand = [k for k in STRATEGIES if strategy.lower() in k.lower()]
        if len(cand) != 1:
            return {"error": f"알 수 없는 전략: {strategy}",
                    "available": list(STRATEGIES)}
        strategy = cand[0]
    res = backtest_symbol(sym, ctx.provider, ctx.cfg, strategy, period=period)
    return _clean({
        "symbol": res.symbol, "strategy": res.strategy, "period": period,
        "metrics": {k: _r(v, 3) for k, v in res.metrics.items()},
        "n_trades": len(res.trades),
        "caveat": "과거 성과는 미래를 보장하지 않습니다. 거래비용·슬리피지 "
                  "가정에 따라 결과가 크게 달라집니다.",
    })


def _render_backtest(d: dict) -> str:
    if d.get("error"):
        return f"❌ {d['error']} (가능: {', '.join(d.get('available', []))})"
    lines = [f"**백테스트** {d['symbol']} · {d['strategy']} · {d['period']}"]
    for k, v in (d.get("metrics") or {}).items():
        lines.append(f"- {k}: {v}")
    lines.append(f"- 매매 횟수: {d['n_trades']}회")
    lines.append(f"\n> ⚠️ {d['caveat']}")
    return "\n".join(lines)


def _tool_news_sentiment(ctx: AssistantContext, symbol: str) -> dict:
    sym = resolve_symbol(symbol) or symbol.upper()
    try:
        news = se.aggregate(ctx.provider.news(sym))
    except Exception as e:
        return {"error": f"뉴스 조회 실패: {e}"}
    return _clean({
        "symbol": sym, "score": _r(news.score, 1), "label": news.label,
        "n_articles": news.n_articles, "n_positive": news.n_positive,
        "n_negative": news.n_negative, "n_neutral": news.n_neutral,
        "confidence": news.confidence, "engine": news.engine,
        "headlines": [{"title": it.title, "publisher": it.publisher,
                       "published": it.published,
                       "sentiment": _r(it.sentiment, 2)}
                      for it in news.items[:8]],
    })


def _render_news_sentiment(d: dict) -> str:
    if d.get("error"):
        return f"❌ {d['error']}"
    if not d["n_articles"]:
        return (f"{d['symbol']}: 수집된 뉴스가 없습니다. "
                "(yahoo 실시간 모드에서 더 잘 동작합니다)")
    lines = [f"**{d['symbol']} 뉴스 분위기** — {d['label']} "
             f"({d['score']}/100, 신뢰도 {d['confidence']})",
             f"- 긍정 {d['n_positive']} · 중립 {d['n_neutral']} · "
             f"부정 {d['n_negative']} (총 {d['n_articles']}건)"]
    for h in d.get("headlines", [])[:5]:
        emo = ("🟢" if (h.get("sentiment") or 0) > 0.05 else
               "🔴" if (h.get("sentiment") or 0) < -0.05 else "⚪")
        lines.append(f"  {emo} {h['title']}")
    return "\n".join(lines)


def _tool_simulate_future(ctx: AssistantContext, symbol: str,
                          horizon_days: int = 126,
                          target: float | None = None) -> dict:
    sym = resolve_symbol(symbol) or symbol.upper()
    try:
        df = ctx.provider.price_history(sym, period="2y")
    except Exception as e:
        return {"error": f"시세 조회 실패: {e}"}
    sim = mcarlo.simulate(df, horizon_days=int(horizon_days), target=target)
    final = sim.percentiles.iloc[-1]
    return _clean({
        "symbol": sym, "start_price": _r(sim.start_price),
        "horizon_days": sim.horizon_days, "n_sims": sim.n_sims,
        "prob_profit": _r(sim.prob_profit, 1),
        "target": _r(sim.target), "prob_target": _r(sim.prob_target, 1),
        "percentiles": {k: _r(final.get(k)) for k in
                        ("p5", "p25", "p50", "p75", "p95") if k in final},
        "caveat": "과거 변동성이 그대로 이어진다는 가정의 몬테카를로 시뮬레이션"
                  "입니다. 실제 분포는 꼬리가 훨씬 두껍습니다.",
    })


def _render_simulate_future(d: dict) -> str:
    if d.get("error"):
        return f"❌ {d['error']}"
    p = d.get("percentiles", {})
    lines = [f"**{d['symbol']} {d['horizon_days']}일 시뮬레이션** "
             f"(현재 ${d['start_price']:,.2f}, {d['n_sims']:,}회)",
             f"- 상승 확률 {d['prob_profit']}%"]
    if p:
        lines.append(f"- 예상 범위: 하위5% ${p.get('p5'):,.2f} · "
                     f"중앙 ${p.get('p50'):,.2f} · 상위5% ${p.get('p95'):,.2f}")
    if d.get("target") is not None:
        lines.append(f"- 목표가 ${d['target']:,.2f} 도달 확률 {d['prob_target']}%")
    lines.append(f"\n> ⚠️ {d['caveat']}")
    return "\n".join(lines)


def _tool_paper_status(ctx: AssistantContext) -> dict:
    b = ctx.load_broker()
    prices = {s: (ctx.price_of(s) or p.avg_price)
              for s, p in b.positions.items()}
    return _clean({
        "cash": _r(b.cash), "initial_cash": _r(b.initial_cash),
        "equity": _r(b.equity(prices)),
        "total_return_pct": _r(b.total_return(prices) * 100, 2),
        "realized_pnl": _r(b.realized_pnl()),
        "holdings": b.holdings_table(prices),
        "n_trades": len(b.trades),
    })


def _render_paper_status(d: dict) -> str:
    if d.get("error"):
        return f"❌ {d['error']}"
    lines = [f"**모의계좌** — 총자산 ${d['equity']:,.2f} "
             f"({_pct(d['total_return_pct'], 2)}), 현금 ${d['cash']:,.2f}"]
    if not d["holdings"]:
        lines.append("- 보유 종목 없음")
    for h in d["holdings"]:
        lines.append(f"- {h['종목']:<6} {h['수량']}주 @ ${h['평균단가']:,.2f} → "
                     f"${h['현재가']:,.2f} ({h['수익률']:+.2f}%, "
                     f"평가손익 ${h['평가손익']:,.2f})")
    lines.append(f"- 실현손익 ${d['realized_pnl']:,.2f} · 거래 {d['n_trades']}회")
    return "\n".join(lines)


def _tool_paper_trade(ctx: AssistantContext, action: str, symbol: str,
                      quantity: float) -> dict:
    sym = resolve_symbol(symbol) or symbol.upper()
    price = ctx.price_of(sym)
    if price is None:
        return {"error": f"{sym} 현재가를 가져오지 못해 주문을 넣지 않았습니다."}
    b = ctx.load_broker()
    try:
        if action == "buy":
            t = b.buy(sym, float(quantity), price)
        elif action == "sell":
            t = b.sell(sym, float(quantity), price)
        else:
            return {"error": f"action 은 buy 또는 sell 이어야 합니다: {action}"}
    except (InsufficientFundsError, InsufficientSharesError, ValueError) as e:
        return {"error": str(e)}
    b.save(ctx.broker_state)
    return _clean({
        "executed": {"action": action, "symbol": sym,
                     "quantity": _r(t.quantity, 4), "price": _r(t.price),
                     "gross": _r(t.gross), "commission": _r(t.commission),
                     "realized_pnl": _r(t.realized_pnl)},
        "cash_after": _r(b.cash),
        "note": "가상 자본 모의매매입니다. 실제 주문이 아닙니다.",
    })


def _render_paper_trade(d: dict) -> str:
    if d.get("error"):
        return f"❌ 체결 실패: {d['error']}"
    e = d["executed"]
    verb = "매수" if e["action"] == "buy" else "매도"
    lines = [f"✅ {e['symbol']} {e['quantity']}주 {verb} @ ${e['price']:,.2f} "
             f"(총 ${e['gross']:,.2f})"]
    if e["action"] == "sell":
        lines.append(f"- 실현손익 ${e['realized_pnl']:,.2f}")
    lines.append(f"- 잔여 현금 ${d['cash_after']:,.2f}")
    lines.append(f"\n> {d['note']}")
    return "\n".join(lines)


def _tool_watchlist_ranking(ctx: AssistantContext, period: str = "1y") -> dict:
    syms = list(ctx.cfg.watchlist)
    results = [analyze_symbol(s, ctx.provider, ctx.cfg, period) for s in syms]
    results.sort(key=lambda r: r.total_score, reverse=True)
    return _clean({
        "criteria": {"top_pct": 100.0, "sector": "관심종목",
                     "scanned": len(syms), "skipped_over_limit": 0},
        "ranking": [
            {"rank": i, "symbol": r.symbol, "name": r.name,
             "total_score": r.total_score, "grade": r.recommendation_label,
             "technical_score": _r(r.technical.score, 1) if r.technical else None,
             "fundamental_score": _r(r.fundamental.score, 1) if r.fundamental else None,
             "sector": r.sector}
            for i, r in enumerate(results, 1)
        ],
        "caveat": SCORE_CAVEAT,
    })


# ----------------------------- 도구 목록 -----------------------------


@dataclass
class ToolSpec:
    name: str
    description: str
    schema: dict
    run: Callable[..., dict]
    render: Callable[[dict], str]
    # 계좌 상태를 바꾸는 도구는 확인 후 실행하도록 표시한다.
    mutates: bool = False
    examples: list[str] = field(default_factory=list)


def _obj(props: dict, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": props, "required": required or []}


_SYMBOL = {"type": "string",
           "description": "티커 또는 회사 이름 (예: NVDA, 엔비디아)"}
_PERIOD = {"type": "string", "enum": ["6mo", "1y", "2y", "5y"],
           "description": "조회 기간 (기본 1y)"}

TOOLS: dict[str, ToolSpec] = {
    t.name: t for t in [
        ToolSpec(
            "analyze_stock",
            "한 종목을 종합 분석한다. 기술적 점수·펀더멘털 점수·종합점수와 "
            "등급, 지표 신호, 최근 뉴스 분위기, 실적 발표일, 판단 근거를 "
            "돌려준다. 특정 종목에 대한 질문에는 항상 이 도구를 먼저 쓴다.",
            _obj({"symbol": _SYMBOL, "period": _PERIOD}, ["symbol"]),
            _tool_analyze_stock, _render_analyze_stock,
            examples=["엔비디아 어때?", "AAPL 분석해줘", "테슬라 점수 알려줘"],
        ),
        ToolSpec(
            "market_overview",
            "S&P500·나스닥·다우 지수의 현재 국면(추세/모멘텀/수급/변동성)과 "
            "방향성 점수, 공포·탐욕 지수, VIX 를 돌려준다. 시장 전반에 대한 "
            "질문에 쓴다.",
            _obj({}),
            _tool_market_overview, _render_market_overview,
            examples=["오늘 시장 어때?", "지금 분위기 어때", "나스닥 상황"],
        ),
        ToolSpec(
            "screen_stocks",
            "시가총액 상위 N% 유니버스를 종합점수로 랭킹한다. 섹터로 좁힐 수 "
            "있다. '점수 높은 종목 찾아줘' 류의 질문에 쓴다.",
            _obj({"top_pct": {"type": "number",
                              "description": "시총 상위 몇 %까지 볼지 (기본 30)"},
                  "sector": {"type": "string",
                             "description": "섹터명 (Technology, Healthcare 등). "
                                            "생략하면 전체"},
                  "limit": {"type": "integer",
                            "description": "상위 몇 종목을 돌려줄지 (기본 10)"},
                  "period": _PERIOD}),
            _tool_screen_stocks, _render_screen_stocks,
            examples=["점수 높은 종목 추천", "기술주 스크리닝", "상위 종목 뽑아줘"],
        ),
        ToolSpec(
            "early_bird",
            "선취매 레이더. 조용한 매집(OBV 상승 + 횡보) 구간에 있고 아직 "
            "급등하지 않은 종목을 찾는다. '먼저 사둘 만한', '아직 안 오른' "
            "류의 질문에 쓴다.",
            _obj({"sector": {"type": "string", "description": "섹터명 (선택)"},
                  "limit": {"type": "integer", "description": "상위 N개 (기본 8)"}}),
            _tool_early_bird, _render_early_bird,
            examples=["선취매 종목 찾아줘", "아직 안 오른 종목", "매집 중인 종목"],
        ),
        ToolSpec(
            "hegemony",
            "헤게모니 스프레드(영업이익 YoY − 매출 YoY)를 계산한다. 이익 "
            "레버리지가 커지는지(가속) 꺾이는지(피크아웃) 본다.",
            _obj({"symbols": {"type": "array", "items": {"type": "string"},
                              "description": "티커 목록 (최대 12개)"}},
                 ["symbols"]),
            _tool_hegemony, _render_hegemony,
            examples=["엔비디아 헤게모니", "MSFT 이익 레버리지", "영업이익 스프레드"],
        ),
        ToolSpec(
            "compare_stocks",
            "여러 종목을 가치·성장·수익성·모멘텀·안정성 5팩터로 비교한다.",
            _obj({"symbols": {"type": "array", "items": {"type": "string"},
                              "description": "비교할 티커 2~6개"}}, ["symbols"]),
            _tool_compare_stocks, _render_compare_stocks,
            examples=["애플이랑 마소 비교", "NVDA vs AMD", "셋 중에 뭐가 나아"],
        ),
        ToolSpec(
            "portfolio_checkup",
            "보유 종목의 분산도·집중도·변동성·베타를 진단하고 리밸런싱을 "
            "제안한다. 종목별 평가금액(USD)이 필요하다.",
            _obj({"holdings": {
                "type": "array",
                "description": "보유 내역",
                "items": _obj({"symbol": _SYMBOL,
                               "value": {"type": "number",
                                         "description": "평가금액 (USD)"}},
                              ["symbol", "value"])}}, ["holdings"]),
            _tool_portfolio_checkup, _render_portfolio_checkup,
            examples=["내 포트폴리오 진단해줘", "분산 잘 됐는지 봐줘"],
        ),
        ToolSpec(
            "backtest",
            "매매 전략을 과거 데이터에 적용해 수익률·MDD·샤프·승률을 단순보유와 "
            f"비교한다. 전략: {', '.join(STRATEGIES)}",
            _obj({"symbol": _SYMBOL,
                  "strategy": {"type": "string", "enum": list(STRATEGIES)},
                  "period": {"type": "string", "enum": ["2y", "5y", "max"]}},
                 ["symbol", "strategy"]),
            _tool_backtest, _render_backtest,
            examples=["AAPL 골든크로스 백테스트", "RSI 전략 검증해줘"],
        ),
        ToolSpec(
            "news_sentiment",
            "종목 관련 최신 헤드라인을 모아 감성분석으로 분위기 점수를 낸다.",
            _obj({"symbol": _SYMBOL}, ["symbol"]),
            _tool_news_sentiment, _render_news_sentiment,
            examples=["테슬라 뉴스 어때?", "엔비디아 분위기"],
        ),
        ToolSpec(
            "simulate_future",
            "몬테카를로로 미래 주가 확률 분포와 목표가 도달 확률을 낸다.",
            _obj({"symbol": _SYMBOL,
                  "horizon_days": {"type": "integer",
                                   "description": "거래일 수 (기본 126 ≈ 6개월)"},
                  "target": {"type": "number", "description": "목표가 (선택)"}},
                 ["symbol"]),
            _tool_simulate_future, _render_simulate_future,
            examples=["엔비디아 6개월 뒤 전망", "AAPL 250달러 갈 확률"],
        ),
        ToolSpec(
            "paper_status",
            "모의매매 계좌의 현금·보유종목·수익률·실현손익을 조회한다.",
            _obj({}),
            _tool_paper_status, _render_paper_status,
            examples=["내 모의계좌 어때?", "수익률 얼마야"],
        ),
        ToolSpec(
            "paper_trade",
            "모의매매 계좌에서 가상 매수/매도를 체결한다(실제 주문 아님). "
            "체결가는 최신 종가다. 사용자가 종목과 수량을 명확히 말했을 때만 "
            "호출하고, 애매하면 먼저 되묻는다.",
            _obj({"action": {"type": "string", "enum": ["buy", "sell"]},
                  "symbol": _SYMBOL,
                  "quantity": {"type": "number", "description": "주식 수"}},
                 ["action", "symbol", "quantity"]),
            _tool_paper_trade, _render_paper_trade, mutates=True,
            examples=["엔비디아 10주 매수", "AAPL 5주 팔아줘"],
        ),
        ToolSpec(
            "watchlist_ranking",
            "config.yaml 관심종목 전체를 종합점수로 랭킹한다.",
            _obj({"period": _PERIOD}),
            _tool_watchlist_ranking, _render_screen_stocks,
            examples=["관심종목 정리해줘", "워치리스트 순위"],
        ),
    ]
}


def anthropic_tool_defs() -> list[dict]:
    """Claude API `tools` 파라미터로 넘길 정의 목록."""
    return [{"name": t.name, "description": t.description,
             "input_schema": t.schema} for t in TOOLS.values()]


def run_tool(ctx: AssistantContext, name: str, args: dict) -> dict:
    """도구를 실행한다. 어떤 예외도 밖으로 던지지 않고 error 로 감싼다.

    모델이 만든 인자는 신뢰할 수 없으므로(없는 키, 잘못된 타입) 실패를
    대화 안에서 복구 가능한 형태로 돌려줘야 루프가 계속 돈다.
    """
    spec = TOOLS.get(name)
    if spec is None:
        return {"error": f"알 수 없는 도구: {name}",
                "available": list(TOOLS)}
    try:
        return spec.run(ctx, **(args or {}))
    except TypeError as e:
        return {"error": f"인자가 맞지 않습니다: {e}",
                "expected": spec.schema}
    except Exception as e:
        return {"error": f"{name} 실행 실패: {type(e).__name__}: {e}"}


def render_tool(name: str, result: dict) -> str:
    """도구 결과를 한국어 텍스트로 렌더링한다.

    렌더러가 예외를 던지더라도 답변 자체는 나가야 하므로 마지막에 원본 dict
    를 보여주는 것으로 대체한다.
    """
    spec = TOOLS.get(name)
    if spec is None:
        return f"❌ 알 수 없는 도구: {name}"
    try:
        return spec.render(result)
    except Exception as e:
        if result.get("error"):
            return f"❌ {result['error']}"
        return f"({name} 결과를 표로 옮기지 못했습니다: {e})\n{result}"
