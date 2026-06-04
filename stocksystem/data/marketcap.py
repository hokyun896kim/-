"""실시간 시가총액 캐시.

'시가총액 상위 N%' 필터의 정확도를 높이기 위해, 유니버스 종목들의 현재
시총을 공급자에서 받아 로컬 JSON 으로 캐시한다. 수백 종목을 매번 조회하면
느리므로 하루 단위로만 갱신한다.

- get_caps(): 캐시된 시총 dict 반환 (없으면 빈 dict)
- refresh(): 공급자에서 시총을 새로 받아 저장 (진행 콜백 지원)
- is_stale(): 캐시가 오래됐는지 확인
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Callable

from .base import DataProvider
from .universe import load_universe

CACHE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "marketcap_cache.json"
_UPDATED_KEY = "_updated"


def load_cache(path: str | Path = CACHE_PATH) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def last_updated(path: str | Path = CACHE_PATH) -> str | None:
    return load_cache(path).get(_UPDATED_KEY)


def is_stale(max_age_days: int = 1, path: str | Path = CACHE_PATH) -> bool:
    """캐시가 없거나 max_age_days 보다 오래됐으면 True."""
    upd = last_updated(path)
    if not upd:
        return True
    try:
        d = datetime.fromisoformat(upd).date()
    except (ValueError, TypeError):
        return True
    return (date.today() - d).days >= max_age_days


def get_caps(path: str | Path = CACHE_PATH) -> dict[str, float]:
    """심볼 -> 시총(USD) 매핑 (메타키 제외)."""
    return {k: v for k, v in load_cache(path).items()
            if k != _UPDATED_KEY and isinstance(v, (int, float))}


def refresh(provider: DataProvider, symbols: list[str] | None = None,
            progress: Callable[[int, int, str], None] | None = None,
            path: str | Path = CACHE_PATH) -> dict[str, float]:
    """공급자에서 시총을 새로 받아 캐시에 저장하고 반환한다.

    progress(done, total, symbol) 콜백으로 진행 상황을 알릴 수 있다.
    개별 종목 조회 실패는 건너뛴다(부분 성공 허용).
    """
    syms = symbols or [s.symbol for s in load_universe()]
    caps: dict[str, float] = {}
    total = len(syms)
    for i, sym in enumerate(syms, 1):
        try:
            mc = provider.market_cap(sym)
            if mc:
                caps[sym] = float(mc)
        except Exception:
            pass
        if progress:
            progress(i, total, sym)

    out = dict(caps)
    out[_UPDATED_KEY] = date.today().isoformat()
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    return caps
