"""헤게모니 스프레드 엔진.

핵심 지표: **헤게모니 스프레드 = 영업이익 증가율(YoY) − 매출 증가율(YoY)**.
매출보다 이익이 빠르게 늘면(+) 가격결정력·고정비 레버리지가 작동한다는 뜻.

- 연간 스프레드: 최근 연간 vs 전년
- 분기 TTM 스프레드: 최근 4분기 합 vs 그 직전 4분기 합 (자료 충분할 때)
- 가속: 분기TTM 스프레드 − 연간 스프레드 (양수면 레버리지 가속 국면)

원본 도구의 철학을 따른다:
- 절대 성장 방향과 함께 본다(둘 다 역성장이면 스프레드 +라도 주도주 아님)
- 전년 이익≈0 기저효과는 비율 폭발 → |가속|>150p 는 신뢰 불가로 처리
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ..data.base import DataProvider, Financials

BASE_EFFECT_CAP = 150.0   # |가속| 이 값 초과면 기저효과로 간주


def _yoy(series: pd.Series | None):
    """가장 최근 vs 직전 값의 YoY(%) 와 (분자, 분모)."""
    if series is None:
        return None
    s = series.dropna()
    if len(s) < 2:
        return None
    cur, prev = float(s.iloc[-1]), float(s.iloc[-2])
    if prev == 0:
        return None
    return (cur / abs(prev) - 1) * 100 if prev > 0 else (cur - prev) / abs(prev) * 100


def _ttm_yoy(series: pd.Series | None):
    """분기 시리즈에서 TTM(최근4분기) YoY(%). 8분기 필요."""
    if series is None:
        return None
    s = series.dropna()
    if len(s) >= 8:
        now = float(s.iloc[-4:].sum())
        prev = float(s.iloc[-8:-4].sum())
        if prev != 0:
            return (now / abs(prev) - 1) * 100 if prev > 0 else (now - prev) / abs(prev) * 100
    # 폴백: 5분기 이상이면 동기(전년 같은 분기) 대비
    if len(s) >= 5:
        cur, yago = float(s.iloc[-1]), float(s.iloc[-5])
        if yago != 0:
            return (cur / abs(yago) - 1) * 100 if yago > 0 else (cur - yago) / abs(yago) * 100
    return None


@dataclass
class HegemonyResult:
    symbol: str
    annual_rev_yoy: float | None = None
    annual_op_yoy: float | None = None
    annual_spread: float | None = None      # 영업이익YoY − 매출YoY (연간)
    ttm_rev_yoy: float | None = None
    ttm_op_yoy: float | None = None
    ttm_spread: float | None = None         # 분기 TTM 스프레드
    accel: float | None = None              # ttm_spread − annual_spread
    base_effect: bool = False               # 기저효과(신뢰 낮음)
    note: str = ""

    @property
    def verdict(self) -> str:
        """간단 판정: 가속/유지/피크아웃/마진압박/데이터부족."""
        if self.annual_spread is None:
            return "데이터 부족"
        if self.annual_spread <= 0:
            return "마진 압박"
        if self.accel is not None and not self.base_effect:
            if self.accel >= 5:
                return "가속 🟢"
            if self.accel <= -10:
                return "피크아웃 🔴"
        return "유지 🟡"


def _round(v):
    return round(v, 1) if v is not None else None


def compute(fin: Financials) -> HegemonyResult:
    """Financials 로부터 헤게모니 스프레드를 계산한다."""
    a_rev = _yoy(fin.annual_revenue)
    a_op = _yoy(fin.annual_op_income)
    annual_spread = (a_op - a_rev) if (a_rev is not None and a_op is not None) else None

    t_rev = _ttm_yoy(fin.quarterly_revenue)
    t_op = _ttm_yoy(fin.quarterly_op_income)
    ttm_spread = (t_op - t_rev) if (t_rev is not None and t_op is not None) else None

    accel = (ttm_spread - annual_spread) if (
        ttm_spread is not None and annual_spread is not None) else None
    base_effect = accel is not None and abs(accel) > BASE_EFFECT_CAP

    note = ""
    if annual_spread is not None and a_rev is not None and a_rev < 0:
        note = "매출 역성장 중 — 스프레드 양수여도 주도주 아닐 수 있음"
    elif base_effect:
        note = "전년 이익이 0 근처 → 가속 비율 폭발(기저효과). 신뢰 낮음"

    return HegemonyResult(
        symbol=fin.symbol.upper(),
        annual_rev_yoy=_round(a_rev), annual_op_yoy=_round(a_op),
        annual_spread=_round(annual_spread),
        ttm_rev_yoy=_round(t_rev), ttm_op_yoy=_round(t_op),
        ttm_spread=_round(ttm_spread),
        accel=None if base_effect else _round(accel),
        base_effect=base_effect, note=note)


def analyze_symbol(symbol: str, provider: DataProvider) -> HegemonyResult:
    try:
        fin = provider.income_statement(symbol)
    except Exception:
        return HegemonyResult(symbol=symbol.upper())
    return compute(fin)


def rank(symbols: list[str], provider: DataProvider) -> list[HegemonyResult]:
    """여러 종목을 연간 스프레드 내림차순으로 정렬."""
    out = [analyze_symbol(s, provider) for s in symbols]
    out.sort(key=lambda r: (r.annual_spread if r.annual_spread is not None
                            else -9999), reverse=True)
    return out
