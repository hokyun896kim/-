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
    turnaround: bool = False                 # 흑자전환(전년 영업이익 ≤ 0)
    quality: str = "—"                       # 스프레드의 질
    reliable: bool = True                    # 기저효과/흑자전환 아니면 True
    note: str = ""

    @property
    def verdict(self) -> str:
        """간단 판정: 기저효과/가속/유지/피크아웃/마진압박/데이터부족."""
        if self.annual_spread is None:
            return "데이터 부족"
        if not self.reliable:
            return "기저효과 ⚠️"
        if self.annual_spread <= 0:
            return "마진 압박"
        if self.accel is not None:
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

    # 흑자전환 감지: 전년(직전) 영업이익이 0 이하면 YoY% 가 급등(산수 착시)
    turnaround = False
    for series in (fin.annual_op_income, fin.quarterly_op_income):
        if series is None:
            continue
        s = series.dropna()
        idx = -2 if series is fin.annual_op_income else -5  # 연간 직전 / 분기 동기
        if len(s) >= abs(idx) and float(s.iloc[idx]) <= 0:
            turnaround = True
            break

    reliable = not (base_effect or turnaround)

    # 스프레드의 질 분류
    if annual_spread is None:
        quality = "—"
    elif not reliable:
        quality = "기저효과(흑자전환·이익 급반등)"
    elif annual_spread <= 0:
        quality = "마진 압박"
    elif a_rev is not None and a_rev >= 5:
        quality = "고품질(매출+이익 동반성장)"
    elif a_rev is not None and a_rev < 0:
        quality = "저품질(매출 역성장 + 비용절감형)"
    else:
        quality = "보통(매출 정체)"

    note = ""
    if not reliable:
        note = ("전년 영업이익이 적자/0 → 증가율(가속) 급등은 흑자전환 착시. "
                "다음 분기부터 정상화될 수 있어 '진짜 체력'은 기저 제거 후 판단 필요")
    elif a_rev is not None and a_rev < 0:
        note = "매출 역성장 중 — 비용절감 기반 스프레드라 지속성 의심"

    return HegemonyResult(
        symbol=fin.symbol.upper(),
        annual_rev_yoy=_round(a_rev), annual_op_yoy=_round(a_op),
        annual_spread=_round(annual_spread),
        ttm_rev_yoy=_round(t_rev), ttm_op_yoy=_round(t_op),
        ttm_spread=_round(ttm_spread),
        accel=None if base_effect else _round(accel),
        base_effect=base_effect, turnaround=turnaround,
        quality=quality, reliable=reliable, note=note)


def analyze_symbol(symbol: str, provider: DataProvider) -> HegemonyResult:
    try:
        fin = provider.income_statement(symbol)
    except Exception:
        return HegemonyResult(symbol=symbol.upper())
    return compute(fin)


def rank(symbols: list[str], provider: DataProvider) -> list[HegemonyResult]:
    """여러 종목 정렬. 신뢰 가능한(기저효과 아닌) 종목을 먼저, 그 안에서 스프레드순.

    → 흑자전환·기저효과로 스프레드가 뻥튀기된 종목이 '가짜 1등'으로 올라오지
       않도록 신뢰도를 1순위 키로 둔다.
    """
    out = [analyze_symbol(s, provider) for s in symbols]
    out.sort(key=lambda r: (
        r.reliable and r.annual_spread is not None,            # 신뢰+데이터 있음 먼저
        r.annual_spread if r.annual_spread is not None else -9999),
        reverse=True)
    return out
