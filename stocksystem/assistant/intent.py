"""규칙 기반 의도 파악 (LLM 없이 동작하는 폴백 엔진).

ANTHROPIC_API_KEY 가 없어도 비서가 쓸모 있으려면, 질문을 도구 하나로
매핑하는 최소한의 이해가 필요하다. 여기서는 키워드 가중치로 도구를 고르고
정규식으로 인자(티커·수량·섹터·기간)를 뽑는다.

정교한 대화는 못 한다 — 그건 Claude 엔진의 몫이다. 이쪽의 목표는
"자주 묻는 열댓 가지를 네트워크·비용 없이 정확히 처리하는 것"이다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..config import Config
from ..data.universe import load_universe
from .tools import KOREAN_ALIASES, TOOLS, resolve_symbol

# 한글 섹터 표현 → 유니버스 CSV 의 섹터명
SECTOR_ALIASES = {
    "기술": "Technology", "테크": "Technology", "it": "Technology",
    "아이티": "Technology", "반도체": "Technology", "소프트웨어": "Technology",
    "헬스케어": "Healthcare", "의료": "Healthcare", "제약": "Healthcare",
    "바이오": "Healthcare",
    "금융": "Financial Services", "은행": "Financial Services",
    "보험": "Financial Services",
    "산업재": "Industrials", "제조": "Industrials", "방산": "Industrials",
    "경기소비재": "Consumer Cyclical", "소비재": "Consumer Cyclical",
    "유통": "Consumer Cyclical",
    "필수소비재": "Consumer Defensive", "생활필수": "Consumer Defensive",
    "통신": "Communication Services", "미디어": "Communication Services",
    "에너지": "Energy", "정유": "Energy", "석유": "Energy",
    "소재": "Basic Materials", "화학": "Basic Materials",
    "유틸리티": "Utilities", "전력": "Utilities",
    "리츠": "Real Estate", "부동산": "Real Estate",
}

# 도구별 트리거 키워드와 가중치. 값이 큰 쪽이 더 결정적인 단서다.
#
# 순서가 아니라 점수로 고르는 이유: "엔비디아 뉴스 어때?" 처럼 두 도구의
# 단서가 같이 나오는 질문이 흔하다. 이때는 더 구체적인 단서(뉴스=3)가
# 기본 동작(종목분석)을 이겨야 한다.
KEYWORDS: dict[str, dict[str, float]] = {
    "paper_status": {"모의계좌": 4, "모의 계좌": 4, "내 계좌": 3, "잔고": 3,
                     "보유종목": 2, "수익률": 2, "실현손익": 3, "계좌": 1.5},
    "portfolio_checkup": {"포트폴리오": 4, "분산": 3, "리밸런싱": 4,
                          "집중도": 3, "베타": 2, "진단": 2},
    "market_overview": {"시장": 3, "지수": 3, "나스닥": 3, "s&p": 3,
                        "에스앤피": 3, "다우": 3, "공포": 3, "탐욕": 3,
                        "vix": 3, "빅스": 3, "장세": 3, "증시": 3},
    "early_bird": {"선취매": 5, "매집": 4, "미리": 2, "먼저": 2,
                   "아직 안 오른": 5, "안오른": 3, "저평가 구간": 3,
                   "레이더": 3, "바닥": 2},
    "hegemony": {"헤게모니": 5, "스프레드": 4, "이익 레버리지": 5,
                 "영업이익": 3, "레버리지": 2, "피크아웃": 4, "마진": 2},
    "backtest": {"백테스트": 5, "백테스팅": 5, "전략": 3, "골든크로스": 4,
                 "검증해": 2, "과거에": 2, "돌려보": 3},
    "news_sentiment": {"뉴스": 4, "기사": 3, "헤드라인": 4, "여론": 3,
                       "분위기": 2},
    "simulate_future": {"시뮬": 4, "몬테카를로": 5, "확률": 3, "전망": 2,
                        "도달": 3, "목표가": 3, "미래": 2},
    "compare_stocks": {"비교": 4, " vs ": 4, "대비": 2, "어느 쪽": 3,
                       "뭐가 나아": 3, "누가 나": 3, "낫나": 3},
    "screen_stocks": {"스크리너": 5, "스크리닝": 5, "랭킹": 3, "순위": 3,
                      "상위": 2, "추천": 2, "찾아": 2, "골라": 2,
                      "좋은 종목": 3, "높은 종목": 3},
    "watchlist_ranking": {"관심종목": 5, "워치리스트": 5, "관심 종목": 5},
    "analyze_stock": {"분석": 2, "어때": 1, "점수": 2, "봐줘": 1, "알려줘": 0.5},
}

_BUY_RE = re.compile(r"(사줘|사자|사도|매수|매입|살까|사고)")
_SELL_RE = re.compile(r"(팔아|팔자|팔까|매도|정리해)")
_QTY_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:주|shares?)")
_MONEY_RE = re.compile(r"([A-Za-z가-힣&^\.\-]+)\s*(?:에|을|를)?\s*"
                       r"\$?\s*([\d,]+(?:\.\d+)?)\s*(?:달러|불|usd|\$)",
                       re.IGNORECASE)
_PCT_RE = re.compile(r"상위\s*(\d+(?:\.\d+)?)\s*%")
_LIMIT_RE = re.compile(r"(\d+)\s*(?:개|종목)")
_TARGET_RE = re.compile(r"\$?\s*([\d,]+(?:\.\d+)?)\s*(?:달러|불|\$)")
_PERIODS = {"6개월": "6mo", "1년": "1y", "2년": "2y", "5년": "5y",
            "6mo": "6mo", "1y": "1y", "2y": "2y", "5y": "5y"}
_HORIZONS = {"1개월": 21, "한 달": 21, "3개월": 63, "6개월": 126,
             "반년": 126, "1년": 252, "일년": 252}


@dataclass
class Intent:
    """규칙 엔진이 고른 도구와 인자."""

    tool: str
    args: dict = field(default_factory=dict)
    confidence: float = 0.0      # 0~1, 키워드 점수를 눌러 담은 값
    note: str = ""               # 사용자에게 덧붙일 안내 (추측한 부분 등)


def extract_symbols(text: str) -> list[str]:
    """문장에서 티커를 등장 순서대로 중복 없이 뽑는다."""
    found: list[str] = []
    low = text.lower()

    # 1) 한글 별칭 — 등장 위치 순으로
    hits = [(low.find(ko.lower()), sym) for ko, sym in KOREAN_ALIASES.items()
            if ko.lower() in low]
    # 2) 대문자 티커 토큰 (BRK-B, ^VIX 포함)
    known = {u.symbol for u in load_universe()}
    for m in re.finditer(r"\^?[A-Z]{1,5}(?:-[A-Z])?", text):
        if m.group(0) in known:
            hits.append((m.start(), m.group(0)))
    # 3) 영문 회사명
    for u in load_universe():
        head = u.name.lower().split(" inc")[0].split(" corp")[0].strip(" .,")
        if len(head) >= 4 and head in low:
            hits.append((low.find(head), u.symbol))

    for _, sym in sorted(hits, key=lambda x: x[0]):
        if sym not in found:
            found.append(sym)
    return found


def extract_sector(text: str) -> str | None:
    low = text.lower()
    for ko, sec in SECTOR_ALIASES.items():
        if ko in low:
            return sec
    for u in load_universe():
        if u.sector.lower() in low:
            return u.sector
    return None


def _num(pattern: re.Pattern, text: str, cast=float):
    m = pattern.search(text)
    if not m:
        return None
    try:
        return cast(m.group(1).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _score_tools(text: str) -> dict[str, float]:
    low = text.lower()
    scores: dict[str, float] = {}
    for tool, kws in KEYWORDS.items():
        s = sum(w for kw, w in kws.items() if kw in low)
        if s:
            scores[tool] = s
    return scores


def parse_intent(text: str, cfg: Config | None = None) -> Intent | None:
    """자연어 → 실행할 도구. 무엇을 원하는지 모르면 None.

    None 을 돌려주는 것도 정상 동작이다. 억지로 도구를 고르는 것보다
    "이런 걸 물어보세요" 라고 안내하는 편이 낫다.
    """
    if not text or not text.strip():
        return None
    text = text.strip()
    low = text.lower()
    symbols = extract_symbols(text)
    scores = _score_tools(text)

    # --- 모의매매는 계좌를 바꾸므로 명시적 신호(수량+동사)를 모두 요구한다 ---
    qty = _num(_QTY_RE, text)
    if qty and symbols:
        if _BUY_RE.search(low):
            return Intent("paper_trade",
                          {"action": "buy", "symbol": symbols[0],
                           "quantity": qty}, 0.95)
        if _SELL_RE.search(low):
            return Intent("paper_trade",
                          {"action": "sell", "symbol": symbols[0],
                           "quantity": qty}, 0.95)

    # --- 포트폴리오: "AAPL 5000달러, MSFT 3000달러" 형태를 먼저 본다 ---
    money = _MONEY_RE.findall(text)
    holdings = []
    for token, amount in money:
        sym = resolve_symbol(token)
        if sym:
            holdings.append({"symbol": sym,
                             "value": float(amount.replace(",", ""))})
    if holdings and (scores.get("portfolio_checkup") or len(holdings) >= 2):
        return Intent("portfolio_checkup", {"holdings": holdings}, 0.9)

    if not scores and not symbols:
        return None

    # 종목이 언급됐으면 종목분석을 기본 후보로 깔아둔다.
    if symbols:
        scores["analyze_stock"] = scores.get("analyze_stock", 0) + 1.5
    if len(symbols) >= 2 and "compare_stocks" in scores:
        scores["compare_stocks"] += 2

    # 종목 없이 "분위기/전망" 만 물으면 개별 분석이 아니라 시장 이야기다.
    if not symbols:
        for tool in ("analyze_stock", "news_sentiment", "simulate_future",
                     "hegemony", "backtest"):
            scores.pop(tool, None)
        if any(k in low for k in ("어때", "분위기", "전망", "상황")):
            scores["market_overview"] = scores.get("market_overview", 0) + 2

    if not scores:
        return None

    tool = max(scores, key=lambda k: scores[k])
    conf = min(0.9, 0.35 + scores[tool] / 10)
    args, note = _build_args(tool, text, low, symbols, cfg)
    return Intent(tool, args, conf, note)


def _build_args(tool: str, text: str, low: str, symbols: list[str],
                cfg: Config | None) -> tuple[dict, str]:
    """고른 도구에 맞춰 인자를 채우고, 추측한 부분을 note 로 알린다."""
    args: dict = {}
    notes: list[str] = []
    period = next((v for k, v in _PERIODS.items() if k in low), None)

    if tool in ("analyze_stock", "news_sentiment"):
        args["symbol"] = symbols[0]
        if tool == "analyze_stock" and period:
            args["period"] = period
        if len(symbols) > 1:
            notes.append(f"{symbols[0]} 기준으로 봤습니다 "
                         f"(여러 종목은 '비교'라고 말해주세요)")

    elif tool in ("hegemony", "compare_stocks"):
        args["symbols"] = symbols or (list(cfg.watchlist)[:4] if cfg else [])
        if not symbols and cfg:
            notes.append("종목을 못 찾아 관심종목으로 대신했습니다")

    elif tool == "simulate_future":
        args["symbol"] = symbols[0]
        horizon = next((v for k, v in _HORIZONS.items() if k in low), None)
        if horizon:
            args["horizon_days"] = horizon
        target = _num(_TARGET_RE, text)
        if target:
            args["target"] = target

    elif tool == "backtest":
        args["symbol"] = symbols[0]
        from ..backtest import STRATEGIES
        strat = next((k for k in STRATEGIES
                      if any(w in low for w in k.lower().split())), None)
        if strat is None:
            for key, name in (("골든", "골든크로스 (SMA 교차)"),
                              ("sma", "골든크로스 (SMA 교차)"),
                              ("rsi", "RSI 역추세"),
                              ("macd", "MACD 추세"),
                              ("점수", "종합 기술점수")):
                if key in low:
                    strat = name
                    break
        if strat is None:
            strat = list(STRATEGIES)[0]
            notes.append(f"전략을 못 찾아 '{strat}' 로 돌렸습니다")
        args["strategy"] = strat
        args["period"] = period if period in ("2y", "5y") else "2y"

    elif tool in ("screen_stocks", "early_bird"):
        sector = extract_sector(text)
        if sector:
            args["sector"] = sector
        limit = _num(_LIMIT_RE, text, int)
        if limit:
            args["limit"] = max(1, min(30, limit))
        if tool == "screen_stocks":
            top_pct = _num(_PCT_RE, text)
            if top_pct:
                args["top_pct"] = top_pct
            if period:
                args["period"] = period
        # 스캔 상한에 걸렸는지는 실제로 돌려봐야 알 수 있다 —
        # 안내는 도구 결과(skipped_over_limit)를 보고 렌더러가 붙인다.

    elif tool == "watchlist_ranking" and period:
        args["period"] = period

    return args, " · ".join(notes)


def suggestions() -> list[str]:
    """무엇을 물어볼 수 있는지 보여줄 예시 문장."""
    out: list[str] = []
    for spec in TOOLS.values():
        out.extend(spec.examples[:1])
    return out
