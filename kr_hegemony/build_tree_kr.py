#!/usr/bin/env python3
"""한국판 헤게모니 트리 데이터 빌더 — tree_kr.json 생성.

헤게모니 스프레드(영업이익YoY − 매출YoY)는 국적과 무관하므로, 미국판과
동일한 분석 틀을 한국 코스피/코스닥 종목에 적용한다.

데이터 소스: yfinance (한국 종목은 .KS=코스피, .KQ=코스닥 접미사).
- 연간/분기 손익계산서 → spread, q_spread, accel
- 시세(종목 vs ^KS11 코스피) → rs3, rs6, gap
- info → pe, fpe, 시가총액

사용:
  python build_tree_kr.py            # 실시간(yfinance) — 인터넷 필요
  python build_tree_kr.py --demo     # 오프라인 데모(합성값) — 네트워크 불필요

출력: data/tree_kr.json  (HTML 도구가 ./data/tree_kr.json 을 읽음)
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, timedelta
from pathlib import Path

# ─────────────────────────── 한국 유니버스 ───────────────────────────
# (티커, 종목명, 대섹터, 세부산업, 세부산업코드)
UNIVERSE = [
    ("005930.KS", "삼성전자", "IT·반도체", "반도체", "SEMI"),
    ("000660.KS", "SK하이닉스", "IT·반도체", "반도체", "SEMI"),
    ("000990.KS", "DB하이텍", "IT·반도체", "반도체", "SEMI"),
    ("058470.KQ", "리노공업", "IT·반도체", "반도체 장비·소재", "SEMIEQ"),
    ("240810.KQ", "원익IPS", "IT·반도체", "반도체 장비·소재", "SEMIEQ"),
    ("357780.KQ", "솔브레인", "IT·반도체", "반도체 장비·소재", "SEMIEQ"),
    ("009150.KS", "삼성전기", "IT·반도체", "전자부품", "ELEC"),
    ("066570.KS", "LG전자", "IT·반도체", "전자부품", "ELEC"),
    ("373220.KS", "LG에너지솔루션", "2차전지·소재", "2차전지", "BATT"),
    ("006400.KS", "삼성SDI", "2차전지·소재", "2차전지", "BATT"),
    ("051910.KS", "LG화학", "2차전지·소재", "2차전지", "BATT"),
    ("247540.KQ", "에코프로비엠", "2차전지·소재", "2차전지 소재", "BATTMAT"),
    ("086520.KQ", "에코프로", "2차전지·소재", "2차전지 소재", "BATTMAT"),
    ("003670.KS", "포스코퓨처엠", "2차전지·소재", "2차전지 소재", "BATTMAT"),
    ("207940.KS", "삼성바이오로직스", "바이오·헬스케어", "바이오", "BIO"),
    ("068270.KS", "셀트리온", "바이오·헬스케어", "바이오", "BIO"),
    ("196170.KQ", "알테오젠", "바이오·헬스케어", "바이오", "BIO"),
    ("028300.KQ", "HLB", "바이오·헬스케어", "바이오", "BIO"),
    ("005380.KS", "현대차", "자동차", "완성차", "AUTO"),
    ("000270.KS", "기아", "자동차", "완성차", "AUTO"),
    ("012330.KS", "현대모비스", "자동차", "자동차 부품", "AUTOPART"),
    ("105560.KS", "KB금융", "금융", "은행·지주", "BANK"),
    ("055550.KS", "신한지주", "금융", "은행·지주", "BANK"),
    ("086790.KS", "하나금융지주", "금융", "은행·지주", "BANK"),
    ("035420.KS", "NAVER", "인터넷·게임", "인터넷 플랫폼", "NET"),
    ("035720.KS", "카카오", "인터넷·게임", "인터넷 플랫폼", "NET"),
    ("259960.KS", "크래프톤", "인터넷·게임", "게임", "GAME"),
    ("036570.KS", "엔씨소프트", "인터넷·게임", "게임", "GAME"),
    ("005490.KS", "POSCO홀딩스", "소재·산업재", "철강·비철", "STEEL"),
    ("010130.KS", "고려아연", "소재·산업재", "철강·비철", "STEEL"),
    ("090430.KS", "아모레퍼시픽", "소비재", "화장품·음식료", "CONS"),
    ("097950.KS", "CJ제일제당", "소비재", "화장품·음식료", "CONS"),
    ("017670.KS", "SK텔레콤", "통신·유틸리티", "통신", "TELCO"),
    ("015760.KS", "한국전력", "통신·유틸리티", "유틸리티", "UTIL"),
]


def _seed(s: str) -> int:
    return int(hashlib.md5(s.encode()).hexdigest(), 16) % (2**32)


def _dart_url(tk: str) -> str:
    """DART 전자공시 검색 (티커 숫자부분으로)."""
    code = tk.split(".")[0]
    return f"https://dart.fss.or.kr/dsab007/main.do?option=corp&textCrpNm={code}"


def _member_synth(tk: str, nm: str) -> dict:
    """오프라인 데모용 합성 헤게모니 지표 (결정론적). 실제와 무관."""
    import numpy as np
    rng = np.random.default_rng(_seed(tk))
    rev = round(float(rng.uniform(-8, 28)), 1)            # 매출 YoY
    spread = round(float(rng.uniform(-12, 28)), 1)        # 연간 스프레드
    op = round(rev + spread, 1)                           # 영업이익 YoY
    # 분기 TTM — 일부는 가속, 일부는 둔화, 일부는 흑자전환 기저
    q_spread = round(spread + float(rng.uniform(-10, 14)), 1)
    accel = round(q_spread - spread, 1)
    # 흑자전환 기저효과 케이스 (가끔)
    q_op = round(op + float(rng.uniform(-5, 20)), 1)
    if rng.random() < 0.15:
        q_op = round(float(rng.uniform(55, 90)), 1)       # 분기 영익 폭등(기저)
    rs6 = round(float(rng.uniform(-30, 45)), 1)           # KOSPI 대비 6M
    # rs3 — 점화/냉각 다양화
    rs3 = round(rs6 * float(rng.uniform(-0.4, 1.6)) + float(rng.uniform(-8, 18)), 1)
    gap = round(float(rng.uniform(2, 12)), 1)
    gaplvl = "H" if gap > 8 else "L" if gap < 4 else "M"
    pe = None if rng.random() < 0.2 else round(float(rng.uniform(6, 40)), 1)
    fpe = None if pe is None or rng.random() < 0.3 else round(pe * 0.9, 1)
    days = int(rng.integers(-30, 70))
    return {
        "tk": tk, "nm": nm, "spread": spread, "q_spread": q_spread,
        "accel": accel, "rs3": rs3, "rs6": rs6, "gap": gap, "gaplvl": gaplvl,
        "op": op, "rev": rev, "q_op": q_op, "pe": pe, "fpe": fpe, "peg": None,
        "q_note": "정상", "d_until": days,
        "ir": {"date": "2026-05", "docs": [
            {"label": "DART 사업·분기보고서", "url": _dart_url(tk)}]},
    }


def _member_yf(tk: str, nm: str, bench) -> dict:
    """실시간(yfinance) 헤게모니 지표. (인터넷 필요)"""
    import numpy as np
    import yfinance as yf

    t = yf.Ticker(tk)

    def yoy(df, names):
        if df is None or getattr(df, "empty", True):
            return None
        for n in names:
            if n in df.index:
                s = df.loc[n].dropna().sort_index()
                if len(s) >= 2 and s.iloc[-2] not in (0,):
                    return round((s.iloc[-1] / abs(s.iloc[-2]) - 1) * 100, 1)
        return None

    def ttm_yoy(df, names):
        if df is None or getattr(df, "empty", True):
            return None
        for n in names:
            if n in df.index:
                s = df.loc[n].dropna().sort_index()
                if len(s) >= 8:
                    now, prev = s.iloc[-4:].sum(), s.iloc[-8:-4].sum()
                    if prev:
                        return round((now / abs(prev) - 1) * 100, 1)
        return None

    REV = ["Total Revenue", "TotalRevenue", "Operating Revenue"]
    OP = ["Operating Income", "OperatingIncome", "Total Operating Income As Reported"]
    a, q = None, None
    try:
        a = t.income_stmt
    except Exception:
        pass
    try:
        q = t.quarterly_income_stmt
    except Exception:
        pass
    rev, op = yoy(a, REV), yoy(a, OP)
    spread = round(op - rev, 1) if (rev is not None and op is not None) else None
    t_rev, t_op = ttm_yoy(q, REV), ttm_yoy(q, OP)
    q_spread = round(t_op - t_rev, 1) if (t_rev is not None and t_op is not None) else None
    accel = round(q_spread - spread, 1) if (q_spread is not None and spread is not None) else None

    # 시세 RS (KOSPI 대비) + gap
    rs3 = rs6 = gap = None
    gaplvl = "M"
    try:
        h = t.history(period="7mo", auto_adjust=True)
        c = h["Close"].dropna()
        if len(c) > 130 and bench is not None and len(bench) > 130:
            def ret(s, n):
                return (s.iloc[-1] / s.iloc[-n] - 1) * 100
            rs3 = round(ret(c, 63) - ret(bench, 63), 1)
            rs6 = round(ret(c, 126) - ret(bench, 126), 1)
        # gap: 최근 60일 전일종가 대비 시가 최대 괴리
        o, pc = h["Open"], h["Close"].shift(1)
        g = ((o - pc).abs() / pc * 100).dropna().iloc[-60:]
        if len(g):
            gap = round(float(g.max()), 1)
            gaplvl = "H" if gap > 8 else "L" if gap < 4 else "M"
    except Exception:
        pass

    info = {}
    try:
        info = t.info or {}
    except Exception:
        pass
    return {
        "tk": tk, "nm": nm, "spread": spread, "q_spread": q_spread,
        "accel": accel, "rs3": rs3, "rs6": rs6, "gap": gap, "gaplvl": gaplvl,
        "op": op, "rev": rev, "q_op": t_op, "pe": info.get("trailingPE"),
        "fpe": info.get("forwardPE"), "peg": info.get("trailingPegRatio"),
        "q_note": "정상", "d_until": None,
        "ir": {"date": datetime.today().strftime("%Y-%m"), "docs": [
            {"label": "DART 사업·분기보고서", "url": _dart_url(tk)}]},
    }


def _median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return 0.0
    n = len(xs)
    return round(xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2, 1)


def build(demo: bool) -> dict:
    bench = None
    if not demo:
        import yfinance as yf
        try:
            bench = yf.Ticker("^KS11").history(period="7mo")["Close"].dropna()
        except Exception:
            bench = None

    # 세부산업별 멤버 구성
    subs_map: dict[str, dict] = {}
    for tk, nm, gics, sub_ko, sub_code in UNIVERSE:
        m = _member_synth(tk, nm) if demo else _member_yf(tk, nm, bench)
        subs_map.setdefault(sub_code, {"sic": sub_code, "ko": sub_ko,
                                       "desc": sub_code, "gics": gics,
                                       "members": []})
        subs_map[sub_code]["members"].append(m)

    subs = []
    for s in subs_map.values():
        s["members"].sort(key=lambda m: (m["spread"] if m["spread"] is not None else -999),
                          reverse=True)
        s["med"] = _median([m["spread"] for m in s["members"]])
        s["n"] = len(s["members"])
        subs.append(s)
    subs.sort(key=lambda s: s["med"], reverse=True)

    # 대섹터 집계
    sec_map: dict[str, list] = {}
    for s in subs:
        sec_map.setdefault(s["gics"], [])
        sec_map[s["gics"]].extend(m["spread"] for m in s["members"])
    sectors = [{"gics": g, "med": _median(v), "n_sub": sum(1 for s in subs if s["gics"] == g),
                "n_co": len(v)} for g, v in sec_map.items()]
    sectors.sort(key=lambda x: x["med"], reverse=True)

    # 시장 배지 (코스피 기준) — 데모는 합성, 실시간은 yfinance
    if demo:
        market = {"vix": 18.5, "vix_state": "경계", "spy3": 4.2, "spy6": 7.8}
    else:
        import yfinance as yf
        def chg(sym, n):
            try:
                c = yf.Ticker(sym).history(period="7mo")["Close"].dropna()
                return round((c.iloc[-1] / c.iloc[-n] - 1) * 100, 1)
            except Exception:
                return None
        vk = None
        try:
            vk = round(float(yf.Ticker("^KS11").history(period="5d")["Close"].iloc[-1]), 0)
        except Exception:
            pass
        market = {"vix": 18.5, "vix_state": "—",
                  "spy3": chg("^KS11", 63), "spy6": chg("^KS11", 126)}

    return {"updated": date.today().isoformat(), "market": market,
            "sectors": sectors, "subs": subs}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="오프라인 합성 데모")
    ap.add_argument("--out", default="data/tree_kr.json")
    args = ap.parse_args()
    tree = build(args.demo)
    out = Path(__file__).resolve().parent / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=1)
    n = sum(len(s["members"]) for s in tree["subs"])
    print(f"✅ {out} 생성 — 섹터 {len(tree['sectors'])} · 세부산업 "
          f"{len(tree['subs'])} · 종목 {n} ({'데모' if args.demo else '실시간'})")


if __name__ == "__main__":
    main()
