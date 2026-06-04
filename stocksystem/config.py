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
class PaperTrading:
    initial_cash: float = 100_000
    commission: float = 0.0


@dataclass
class Config:
    watchlist: list[str] = field(default_factory=lambda: ["AAPL", "MSFT", "NVDA"])
    data_provider: str = "yahoo"
    technical: TechnicalConfig = field(default_factory=TechnicalConfig)
    weights: Weights = field(default_factory=Weights)
    recommendation: Recommendation = field(default_factory=Recommendation)
    paper_trading: PaperTrading = field(default_factory=PaperTrading)


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
        weights=_build(Weights, raw.get("weights")),
        recommendation=_build(Recommendation, raw.get("recommendation")),
        paper_trading=_build(PaperTrading, raw.get("paper_trading")),
    )
