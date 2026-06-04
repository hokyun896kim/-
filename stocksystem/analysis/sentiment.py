"""뉴스 감성 분석 (경량 사전 기반).

외부 모델/네트워크 없이 동작하도록 금융 도메인 긍정/부정 단어 사전으로
헤드라인의 분위기를 점수화한다. 정교한 NLP는 아니지만, 개인투자자가
'요즘 이 종목 뉴스 분위기가 어떤지' 빠르게 파악하는 데 충분하다.

- score_text(): 한 문장 -> -1.0 ~ +1.0
- aggregate(): 여러 뉴스 -> 종합 분위기 점수(0~100) + 라벨
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..data.base import NewsItem

# 금융 뉴스에서 자주 쓰이는 긍정/부정 표현 (소문자)
POSITIVE = {
    "beat", "beats", "surge", "surges", "soar", "soars", "rally", "rallies",
    "gain", "gains", "jump", "jumps", "rise", "rises", "record", "high",
    "strong", "growth", "grow", "outperform", "upgrade", "upgraded", "buy",
    "bullish", "profit", "profits", "boost", "boosts", "win", "wins",
    "expansion", "innovative", "breakthrough", "raise", "raises", "raised",
    "top", "tops", "exceed", "exceeds", "exceeded", "momentum", "optimistic",
    "positive", "approval", "approved", "partnership", "demand", "robust",
    "accelerate", "leading", "dividend", "buyback", "upside",
}
NEGATIVE = {
    "miss", "misses", "missed", "plunge", "plunges", "drop", "drops", "fall",
    "falls", "slump", "slumps", "decline", "declines", "loss", "losses",
    "weak", "weakness", "downgrade", "downgraded", "sell", "bearish",
    "warning", "warn", "warns", "cut", "cuts", "slash", "slashes", "lawsuit",
    "probe", "investigation", "recall", "delay", "delayed", "concern",
    "concerns", "risk", "risks", "fear", "fears", "slowdown", "layoff",
    "layoffs", "fraud", "default", "bankruptcy", "crash", "tumble", "tumbles",
    "disappointing", "disappoint", "underperform", "halt", "halts", "fine",
    "decline", "pressure", "headwind", "headwinds", "downside", "selloff",
}

# 부정어 (뒤 단어의 의미를 뒤집음)
NEGATORS = {"no", "not", "never", "without", "fails", "fail", "failed"}

_WORD_RE = re.compile(r"[a-zA-Z']+")


def score_text(text: str) -> float:
    """문장의 감성 점수 (-1.0 ~ +1.0). 단어가 없으면 0."""
    if not text:
        return 0.0
    words = _WORD_RE.findall(text.lower())
    score = 0
    hits = 0
    for i, w in enumerate(words):
        val = 0
        if w in POSITIVE:
            val = 1
        elif w in NEGATIVE:
            val = -1
        if val:
            # 직전 단어가 부정어면 부호 반전
            if i > 0 and words[i - 1] in NEGATORS:
                val = -val
            score += val
            hits += 1
    if hits == 0:
        return 0.0
    # 단어 수로 정규화하지 않고 hits 로 나눠 -1~1 유지
    return max(-1.0, min(1.0, score / hits))


def label_for(value_0_100: float) -> str:
    """0~100 점수를 한글 분위기 라벨로."""
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
    items: list[NewsItem] = field(default_factory=list)


def aggregate(news: list[NewsItem]) -> NewsSentiment:
    """뉴스 목록을 분석해 종합 분위기를 산출하고 각 기사에 감성을 채운다."""
    if not news:
        return NewsSentiment(score=50.0, label="뉴스 없음", n_articles=0)

    pos = neg = neu = 0
    total = 0.0
    for item in news:
        text = " ".join(filter(None, [item.title, item.summary or ""]))
        s = score_text(text)
        item.sentiment = round(s, 3)
        total += s
        if s > 0.05:
            pos += 1
        elif s < -0.05:
            neg += 1
        else:
            neu += 1

    avg = total / len(news)              # -1 ~ +1
    score = round((avg + 1) / 2 * 100, 1)  # 0 ~ 100
    return NewsSentiment(score=score, label=label_for(score),
                         n_articles=len(news), n_positive=pos,
                         n_negative=neg, n_neutral=neu, items=news)
