"""설정 로딩 모듈.

config.yaml 을 읽어 dataclass 형태의 타입 안전한 설정 객체로 변환한다.
파일이 없거나 항목이 비어 있으면 기본값을 사용한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


@dataclass
class TechnicalConfig:
    sma_short: int = 20
    sma_long: int = 50
    ema_period: int = 20
    rsi_period: int = 14
    rsi_overbought: float = 70
    rsi_oversold: float = 30
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    bb_period: int = 20
    bb_std: float = 2.0
    # 기술 점수에서 추세추종 성분(SMA교차·가격위치·MACD)에 줄 가중치.
    #
    # 0.0 이 기본값이다. 검증 결과 추세추종 성분은 **예측 방향이 반대**였다 —
    # 80종목 전 기간에서 단조성 -1.00(다섯 구간이 완벽한 역순), IC t=-3.04
    # (다중검정 보정 통과), 유니버스 편향 제거 후 연 -6.89%. 20일·60일
    # 양쪽에서 일관됐다. 근거: data/validation.json, 대시보드 🔬 검증 화면.
    #
    # 1.0 = 순수 추세추종, 0.5 = 다섯 신호 균등평균(옛 기본값).
    trend_weight: float = 0.0


@dataclass
class Weights:
    technical: float = 0.5
    fundamental: float = 0.5


@dataclass
class Recommendation:
    strong_buy: float = 75
    buy: float = 60
    hold: float = 40
    sell: float = 25


@dataclass
class FundamentalConfig:
    """펀더멘털 채점 방식.

    sector_neutral=False (기본): PER/PBR/부채비율을 절대 구간으로 채점.
      섹터 무관 고정 기준이라 은행·통신이 구조적으로 고득점하고 고성장
      기술주가 감점된다 — 의도치 않은 밸류 팩터 베팅이 섞인다.
    sector_neutral=True: 같은 섹터 안에서의 백분위로 채점해 그 편향을 없앤다.

    어느 쪽이 실제로 나은지는 point-in-time 재무 데이터가 없어 아직 검증
    불가다. 그래서 기본값은 기존 동작(False)으로 두고 옵트인으로 제공한다.
    """
    sector_neutral: bool = False
    min_peers: int = 4


@dataclass
class PaperTrading:
    initial_cash: float = 100_000
    commission: float = 0.0


@dataclass
class AssistantConfig:
    """AI 비서 설정.

    engine="auto" 면 자격증명이 있을 때만 Claude 를 쓰고, 없으면 규칙 엔진으로
    내려간다. 키가 없는 사람도 그대로 쓸 수 있게 하려는 기본값이다.
    """

    engine: str = "auto"                  # auto | claude | rules
    model: str = "claude-opus-5"
    max_tokens: int = 16000
    max_turns: int = 6                    # 한 질문에 허용할 도구 호출 라운드
    # 대화창 응답성이 중요하고 무거운 계산은 파이썬 도구가 하므로 medium.
    # 더 촘촘한 추론이 필요하면 high/xhigh 로 올린다.
    effort: str = "medium"
    thinking: str = "adaptive"            # adaptive | off


@dataclass
class Config:
    watchlist: list[str] = field(default_factory=lambda: ["AAPL", "MSFT", "NVDA"])
    data_provider: str = "yahoo"
    technical: TechnicalConfig = field(default_factory=TechnicalConfig)
    fundamental: FundamentalConfig = field(default_factory=FundamentalConfig)
    weights: Weights = field(default_factory=Weights)
    recommendation: Recommendation = field(default_factory=Recommendation)
    paper_trading: PaperTrading = field(default_factory=PaperTrading)
    assistant: AssistantConfig = field(default_factory=AssistantConfig)


def _build(cls, data: dict[str, Any] | None):
    """dict 에서 알려진 필드만 추려 dataclass 를 생성한다."""
    if not data:
        return cls()
    valid = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in data.items() if k in valid})


def load_config(path: str | Path | None = None) -> Config:
    """config.yaml 을 로드한다. 없으면 전부 기본값."""
    p = Path(path) if path else CONFIG_PATH
    raw: dict[str, Any] = {}
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

    return Config(
        watchlist=raw.get("watchlist") or Config().watchlist,
        data_provider=raw.get("data_provider", "yahoo"),
        technical=_build(TechnicalConfig, raw.get("technical")),
        fundamental=_build(FundamentalConfig, raw.get("fundamental")),
        weights=_build(Weights, raw.get("weights")),
        recommendation=_build(Recommendation, raw.get("recommendation")),
        paper_trading=_build(PaperTrading, raw.get("paper_trading")),
        assistant=_build(AssistantConfig, raw.get("assistant")),
    )
