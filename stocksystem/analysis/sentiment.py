"""뉴스 감성 분석 (고도화).

엔진은 VADER(규칙 기반 감성 분석)를 사용하고, 금융 도메인 전용 어휘를
보강해 'beat/miss/downgrade/guidance' 같은 표현을 제대로 평가한다.
VADER는 부정어(not), 강조어(sharply), 대문자/문장부호까지 반영하며
사전이 패키지에 내장돼 있어 **네트워크 없이도** 동작한다.

추가 고도화 요소:
- 제목 + 요약(본문)을 가중 결합 (제목 비중 ↑)
- 최신 기사일수록 높은 가중치 (recency weighting)
- 기사 수·일관성 기반 신뢰도(confidence)

vaderSentiment 미설치 시에는 경량 사전 폴백으로 자동 전환된다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime

from ..data.base import NewsItem

# ---- 금융 도메인 어휘 (VADER 스케일 대략 -4 ~ +4) ----
# VADER 기본 사전에 없거나 일반어 의미와 다른 금융 표현을 보강한다.
FINANCE_LEXICON: dict[str, float] = {
    # 실적/가이던스
    "beat": 2.6, "beats": 2.6, "beating": 2.4, "miss": -2.6, "misses": -2.6,
    "missed": -2.6, "guidance": 0.2, "outlook": 0.0, "forecast": 0.0,
    "raises": 1.8, "raised": 1.8, "lifts": 1.6, "boosts": 1.8, "cuts": -1.9,
    "cut": -1.6, "slashes": -2.4, "slashed": -2.4, "lowers": -1.6,
    "guides": 0.0, "topped": 2.2, "tops": 2.0, "exceeds": 2.2,
    "exceeded": 2.2, "disappoints": -2.4, "disappointing": -2.4,
    # 주가 움직임
    "surge": 3.0, "surges": 3.0, "surged": 3.0, "soar": 3.1, "soars": 3.1,
    "rally": 2.2, "rallies": 2.2, "jumps": 2.2, "jump": 2.0, "rises": 1.4,
    "climb": 1.6, "climbs": 1.6, "plunge": -3.0, "plunges": -3.0,
    "plunged": -3.0, "tumble": -2.6, "tumbles": -2.6, "slump": -2.6,
    "slumps": -2.6, "slides": -1.8, "sinks": -2.4, "drops": -1.6,
    "falls": -1.4, "selloff": -2.4, "sell-off": -2.4, "crash": -3.4,
    # 애널리스트 액션
    "upgrade": 2.6, "upgrades": 2.6, "upgraded": 2.6, "downgrade": -2.6,
    "downgrades": -2.6, "downgraded": -2.6, "bullish": 2.6, "bearish": -2.6,
    "outperform": 2.2, "underperform": -2.2, "overweight": 1.6,
    "underweight": -1.6, "buy": 1.4, "sell": -1.2, "upside": 1.8,
    "downside": -1.8,
    # 기업 이벤트
    "buyback": 1.8, "buybacks": 1.8, "dividend": 1.2, "dividends": 1.2,
    "lawsuit": -2.2, "lawsuits": -2.2, "probe": -1.8, "investigation": -1.8,
    "recall": -2.2, "recalls": -2.2, "layoff": -2.0, "layoffs": -2.0,
    "bankruptcy": -3.6, "default": -2.8, "fraud": -3.4, "halt": -1.8,
    "halts": -1.8, "fine": -1.4, "settlement": -0.8, "subpoena": -1.8,
    "partnership": 1.6, "acquisition": 0.8, "merger": 0.6, "approval": 2.0,
    "approved": 2.0, "rejected": -2.0, "breakthrough": 2.6,
    # 펀더멘털 톤
    "growth": 1.6, "record": 1.8, "robust": 2.0, "strong": 1.9, "solid": 1.5,
    "weak": -1.9, "weakness": -1.9, "soft": -1.2, "headwind": -1.6,
    "headwinds": -1.6, "tailwind": 1.4, "momentum": 1.4, "demand": 1.2,
    "slowdown": -1.8, "recession": -2.4, "pressure": -1.2, "concern": -1.4,
    "concerns": -1.4, "warning": -2.0, "warns": -2.0, "risk": -1.0,
    "profit": 1.6, "profitable": 1.8, "loss": -1.8, "losses": -1.8,
}

# ---- 폴백 경량 사전 (vader 미설치 시) ----
_POS = {w for w, v in FINANCE_LEXICON.items() if v > 0}
_NEG = {w for w, v in FINANCE_LEXICON.items() if v < 0}
_NEGATORS = {"no", "not", "never", "without", "fails", "fail", "failed"}
_WORD_RE = re.compile(r"[a-zA-Z'-]+")

# ---- VADER 엔진 초기화 (1회) ----
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _VADER = SentimentIntensityAnalyzer()
    _VADER.lexicon.update(FINANCE_LEXICON)   # 금융 어휘 보강
except Exception:  # pragma: no cover - 미설치 환경
    _VADER = None


def engine_name() -> str:
    return "VADER+finance" if _VADER else "lexicon"


def _fallback_score(text: str) -> float:
    words = _WORD_RE.findall(text.lower())
    score = hits = 0
    for i, w in enumerate(words):
        val = 1 if w in _POS else -1 if w in _NEG else 0
        if val:
            if i > 0 and words[i - 1] in _NEGATORS:
                val = -val
            score += val
            hits += 1
    return 0.0 if hits == 0 else max(-1.0, min(1.0, score / hits))


def score_text(text: str) -> float:
    """문장의 감성 점수 (-1.0 ~ +1.0)."""
    if not text:
        return 0.0
    if _VADER is not None:
        return _VADER.polarity_scores(text)["compound"]
    return _fallback_score(text)


def score_item(item: NewsItem) -> float:
    """제목 + 요약을 가중 결합한 기사 감성 (-1 ~ +1).

    제목이 핵심이므로 비중을 높게(0.7), 요약은 보조(0.3)로 둔다.
    """
    title_s = score_text(item.title or "")
    if item.summary:
        return round(0.7 * title_s + 0.3 * score_text(item.summary), 4)
    return round(title_s, 4)


def _recency_weight(published: str | None, today: date | None = None) -> float:
    """기사 발행일 기준 가중치 (최근일수록 1.0에 가깝게).

    반감기 14일: 오늘=1.0, 14일 전≈0.5, 28일 전≈0.25. 날짜 없으면 0.6.
    """
    if not published:
        return 0.6
    today = today or date.today()
    try:
        d = datetime.fromisoformat(str(published)[:10]).date()
    except (ValueError, TypeError):
        return 0.6
    age = max(0, (today - d).days)
    return max(0.15, 0.5 ** (age / 14))


def label_for(value_0_100: float) -> str:
    if value_0_100 >= 65:
        return "긍정적 😀"
    if value_0_100 >= 55:
        return "다소 긍정 🙂"
    if value_0_100 > 45:
        return "중립 😐"
    if value_0_100 > 35:
        return "다소 부정 🙁"
    return "부정적 😟"


@dataclass
class NewsSentiment:
    score: float                 # 0~100 (50=중립)
    label: str
    n_articles: int
    n_positive: int = 0
    n_negative: int = 0
    n_neutral: int = 0
    confidence: str = "—"        # 높음/보통/낮음
    engine: str = "—"
    items: list[NewsItem] = field(default_factory=list)


def _confidence(n: int, compounds: list[float]) -> str:
    """기사 수와 의견 일관성으로 신뢰도를 매긴다."""
    if n == 0:
        return "—"
    # 표준편차가 작을수록(의견 일치) 신뢰도 ↑
    mean = sum(compounds) / n
    var = sum((c - mean) ** 2 for c in compounds) / n
    std = var ** 0.5
    if n >= 5 and std < 0.35:
        return "높음"
    if n >= 3 and std < 0.55:
        return "보통"
    return "낮음"


def aggregate(news: list[NewsItem], today: date | None = None) -> NewsSentiment:
    """뉴스 목록을 분석해 종합 분위기를 산출하고 각 기사에 감성을 채운다.

    최신 기사일수록 종합 점수에 더 크게 반영한다(최신성 가중).
    """
    if not news:
        return NewsSentiment(score=50.0, label="뉴스 없음", n_articles=0,
                             engine=engine_name())

    pos = neg = neu = 0
    weighted_sum = weight_total = 0.0
    compounds: list[float] = []
    for item in news:
        s = score_item(item)
        item.sentiment = s
        compounds.append(s)
        w = _recency_weight(item.published, today)
        weighted_sum += s * w
        weight_total += w
        if s > 0.05:
            pos += 1
        elif s < -0.05:
            neg += 1
        else:
            neu += 1

    avg = weighted_sum / weight_total if weight_total else 0.0  # -1 ~ +1
    score = round((avg + 1) / 2 * 100, 1)                       # 0 ~ 100
    return NewsSentiment(
        score=score, label=label_for(score), n_articles=len(news),
        n_positive=pos, n_negative=neg, n_neutral=neu,
        confidence=_confidence(len(news), compounds),
        engine=engine_name(), items=news)
