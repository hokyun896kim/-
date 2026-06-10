"""모닝브리핑 에이전트 — 관심종목(미국+한국) + 시장 심층 브리핑을 reports/에 생성.

사용: python brief.py            (저장소 어디서든 — 경로 자동 해석)
구동: Windows 작업 스케줄러(매일 08:00) 또는 run-once.bat 더블클릭

5요소: LLM(llm_providers 폴백 체인) · 루프(일 1회 스케줄) · 메모리(history.json)
       · 도구(stocksystem/kr_hegemony 모듈) · 목표(브리핑 1건 생성, 10분/500원 한도)
"""
from __future__ import annotations

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import datetime
import json
import pathlib
import time
import traceback

AGENT_DIR = pathlib.Path(__file__).resolve().parent
ROOT = AGENT_DIR.parents[1]  # 저장소 루트 (agents/morning-brief/ 기준)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "kr_hegemony"))
sys.path.insert(0, str(AGENT_DIR))

import numpy as np  # noqa: E402

import llm_providers  # noqa: E402
from stocksystem.config import load_config  # noqa: E402
from stocksystem.data import get_provider  # noqa: E402
from stocksystem.analysis import analyze_symbol  # noqa: E402
from stocksystem.analysis import fundamental as fa  # noqa: E402
from stocksystem.analysis import hegemony as hg  # noqa: E402
from stocksystem.analysis import market as mk  # noqa: E402
from stocksystem.analysis import montecarlo as mc  # noqa: E402
from stocksystem.analysis import technical as ta  # noqa: E402

MAX_RUNTIME_SEC = 600          # 🛑 전체 10분 한도
RUN_COST_LIMIT_KRW = 500       # 💰 1회 한도
MONTH_COST_LIMIT_KRW = 15000   # 💰 월 누적 한도
HISTORY = AGENT_DIR / "history.json"
ERROR_LOG = AGENT_DIR / "error.log"
START = time.time()


def log_error(msg: str) -> None:
    ts = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"{ts} | morning-brief | {msg}\n")


def load_history() -> dict:
    if HISTORY.exists():
        try:
            return json.loads(HISTORY.read_text(encoding="utf-8"))
        except Exception:
            log_error("history.json parse fail - resetting")
    return {"version": 1, "agent_id": "morning-brief", "runs": []}


def month_cost(hist: dict) -> float:
    ym = datetime.date.today().strftime("%Y-%m")
    return sum(r.get("cost_krw", 0) for r in hist["runs"]
               if str(r.get("date", "")).startswith(ym))


def load_watchlist() -> list[str]:
    path = AGENT_DIR / "watchlist.txt"
    if not path.exists():
        return ["AAPL", "MSFT", "NVDA"]
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.split("#")[0].strip()
        if s:
            out.append(s)
    return out


def candidates(raw: str) -> list[str]:
    """한국 6자리 코드 → .KS 우선, 실패 시 .KQ. 그 외는 대문자 그대로."""
    s = raw.strip().upper()
    if s.isdigit() and len(s) == 6:
        return [f"{s}.KS", f"{s}.KQ"]
    return [s]


def is_kr(sym: str) -> bool:
    return sym.endswith(".KS") or sym.endswith(".KQ")


def probe_live() -> bool:
    """야후 라이브 가용 여부 1회 탐침 (조용한 품질 저하 차단 — 형제 스킬 실측 교훈)."""
    try:
        df = get_provider("yahoo").price_history("SPY", period="5d")
        return df is not None and len(df.dropna()) > 0
    except Exception:
        return False


def collect_symbol(provider, provider_name: str, raw: str, cfg) -> dict:
    """한 종목의 심층 데이터 수집. 실패 항목은 None — 절대 중단하지 않는다."""
    d: dict = {"raw": raw, "provider": provider_name}
    sym = None
    for cand in candidates(raw):
        try:
            df = provider.price_history(cand, period="1y")
            if df is not None and len(df.dropna()) > 20:
                sym, d["df"] = cand, df
                break
        except Exception:
            continue
    if sym is None:
        d["error"] = "가격 데이터 수집 실패"
        return d
    d["symbol"], d["kr"] = sym, is_kr(sym)
    try:
        res = analyze_symbol(sym, provider, cfg, "1y")
        d["total"] = res.total_score
        d["label"] = res.recommendation_label
        d["reasons"] = list(res.reasons or [])
        d["name"] = res.name or sym
    except Exception as e:
        log_error(f"{sym} scoring fail: {e}")
    try:
        t = ta.analyze(d["df"], cfg.technical, symbol=sym)
        d["tech_score"] = t.score
        d["signals"] = dict(t.signals)
        d["latest"] = {k: round(v, 2) for k, v in t.latest.items()}
    except Exception as e:
        log_error(f"{sym} technical fail: {e}")
    try:
        f = provider.fundamentals(sym)
        fr = fa.analyze(f)
        d["fund_score"] = fr.score
        d["fund_metrics"] = fr.metric_scores
        d["fund_raw"] = {k: v for k, v in f.to_dict().items()
                         if v is not None and k not in ("symbol",)}
        d["fund_notes"] = list(fr.notes or [])
    except Exception as e:
        log_error(f"{sym} fundamental fail: {e}")
    try:
        h = hg.analyze_symbol(sym, provider)
        d["hegemony"] = (f"연간 스프레드 {h.annual_spread} · TTM {h.ttm_spread} · "
                         f"가속 {h.accel} → {h.verdict}")
    except Exception:
        d["hegemony"] = None
    try:
        s = mc.simulate(d["df"], horizon_days=126)
        fp = s.final_prices
        d["montecarlo"] = (f"6개월 상승확률 {s.prob_profit:.1f}% · 중앙값 "
                           f"{np.percentile(fp, 50):,.2f} · 비관(p5) {np.percentile(fp, 5):,.2f}"
                           f" · 낙관(p95) {np.percentile(fp, 95):,.2f}")
    except Exception:
        d["montecarlo"] = None
    try:
        ev = provider.events(sym)
        d["next_earnings"] = ev.next_earnings_date
    except Exception:
        d["next_earnings"] = None
    if d["kr"]:
        try:
            import naver
            d["kr_enrich"] = naver.enrich(sym.split(".")[0], days=20)
        except Exception:
            d["kr_enrich"] = None
    d.pop("df", None)
    return d


def market_context(provider, cfg, need_us: bool, need_kr: bool) -> list[str]:
    lines = []
    idx = []
    if need_us:
        idx += [("^IXIC", "나스닥"), ("^GSPC", "S&P500")]
    if need_kr:
        idx += [("^KS11", "코스피"), ("^KQ11", "코스닥")]
    for sym, name in idx:
        if time.time() - START > MAX_RUNTIME_SEC:
            lines.append("⚠️ 시간 한도 초과 — 잔여 지수 생략")
            break
        try:
            df = provider.price_history(sym, period="2y")
            r = mk.analyze_index(df, cfg.technical, symbol=sym, name=name)
            lines.append(f"- **{name}** {r.price:,.2f} ({r.change_pct:+.2f}%) — "
                         f"방향성 {r.direction_score:.0f} {r.direction_label} · {r.trend}")
        except Exception as e:
            lines.append(f"- {name}: 수집 실패 ({type(e).__name__})")
    for region, symref in (("미국", "SPY"), ("한국", "^KS11")):
        if (region == "미국" and not need_us) or (region == "한국" and not need_kr):
            continue
        try:
            fg = mk.fear_greed(provider, cfg.technical, market_symbol=symref)
            lines.append(f"- 공포·탐욕({region} 기준): {fg.score:.0f} {fg.label}")
        except Exception:
            pass
    return lines


def fmt_symbol_section(d: dict) -> str:
    if "error" in d:
        return f"### {d['raw']} — ⚠️ {d['error']} (건너뜀)\n"
    cur = "₩" if d.get("kr") else "$"
    price = d.get("latest", {}).get("close")
    out = [f"### {d.get('name', d['raw'])} ({d['symbol']})",
           "",
           f"| 종합점수 | 등급 | 기술 | 펀더멘털 | 현재가 |",
           f"|---|---|---|---|---|",
           f"| {d.get('total', '—')} | **{d.get('label', '—')}** | "
           f"{d.get('tech_score', '—')} | {d.get('fund_score', '—')} | "
           f"{cur}{price:,.2f} |" if price else
           f"| {d.get('total', '—')} | **{d.get('label', '—')}** | "
           f"{d.get('tech_score', '—')} | {d.get('fund_score', '—')} | — |",
           ""]
    if d.get("latest"):
        L = d["latest"]
        out.append(f"- 지표: RSI {L.get('rsi', '—')} · MACD히스토 {L.get('macd_hist', '—')} · "
                   f"볼린저%B {L.get('bb_pct', '—')} · SMA20 {L.get('sma20', '—')} · "
                   f"SMA50 {L.get('sma50', '—')}")
    if d.get("signals"):
        out.append("- 신호: " + " · ".join(f"{k}:{v}" for k, v in d["signals"].items()))
    if d.get("fund_raw"):
        fr = d["fund_raw"]
        parts = []
        for label, key, mul, suffix in (("PER", "trailing_pe", 1, "배"),
                                        ("PBR", "price_to_book", 1, "배"),
                                        ("ROE", "return_on_equity", 100, "%"),
                                        ("순이익률", "profit_margin", 100, "%"),
                                        ("매출성장", "revenue_growth", 100, "%"),
                                        ("부채비율", "debt_to_equity", 1, "%")):
            v = fr.get(key)
            if v is not None:
                parts.append(f"{label} {v * mul:.1f}{suffix}")
        if parts:
            out.append("- 펀더멘털: " + " · ".join(parts))
    if d.get("fund_notes"):
        out.append("- 노트: " + " / ".join(d["fund_notes"]))
    if d.get("hegemony"):
        out.append(f"- 헤게모니 스프레드: {d['hegemony']}")
    if d.get("montecarlo"):
        out.append(f"- 몬테카를로: {d['montecarlo']} (과거 변동성 기반 — 예측 아님)")
    if d.get("kr_enrich"):
        e = d["kr_enrich"]
        out.append(f"- 네이버 보강: PER {e.get('per') or '정보 없음'} · "
                   f"외국인 지분율 {e.get('foreign_pct') or '정보 없음'} · "
                   f"외국인/기관 순매수 {e.get('foreign_net') or '정보 없음'}/"
                   f"{e.get('inst_net') or '정보 없음'}")
    if d.get("reasons"):
        out.append("- 판단 근거: " + " / ".join(d["reasons"]))
    if d.get("next_earnings"):
        out.append(f"- 다음 실적발표: {d['next_earnings']}")
    out.append("")
    return "\n".join(out)


def llm_section(symbols: list[dict], market_lines: list[str], live: bool,
                hist: dict) -> tuple[str, str | None, float]:
    """LLM 종합 해설 — 비용 가드 통과 시에만. 실패·초과 시 모듈 데이터만으로 대체."""
    if month_cost(hist) >= MONTH_COST_LIMIT_KRW:
        return "_(월 비용 한도 도달 — LLM 해설 생략)_", None, 0.0
    system = (AGENT_DIR / "skills" / "MB-01_morning_brief" / "SKILL.md").read_text(
        encoding="utf-8")
    summary = {"샘플데이터경고": (not live),
               "시장": market_lines,
               "종목": [{k: v for k, v in d.items() if k != "df"} for d in symbols]}
    text, provider, cost = llm_providers.generate(
        system, json.dumps(summary, ensure_ascii=False, default=str), max_tokens=2000)
    if text is None:
        return "_(LLM 키 없음 또는 전체 실패 — 위 모듈 데이터를 직접 참고하세요)_", None, 0.0
    if cost > RUN_COST_LIMIT_KRW:
        log_error(f"run cost {cost} KRW exceeded limit {RUN_COST_LIMIT_KRW}")
    return text, provider, cost


def main() -> int:
    today = datetime.date.today().isoformat()
    cfg = load_config()
    watch = load_watchlist()
    live = probe_live()
    provider_name = "yahoo" if live else "sample"
    provider = get_provider(provider_name)

    symbols = []
    for raw in watch:
        if time.time() - START > MAX_RUNTIME_SEC:
            log_error(f"runtime limit - skipped from {raw}")
            symbols.append({"raw": raw, "error": "시간 한도 초과로 생략"})
            continue
        symbols.append(collect_symbol(provider, provider_name, raw, cfg))

    need_kr = any(d.get("kr") for d in symbols)
    need_us = any(not d.get("kr", False) and "error" not in d for d in symbols) or not need_kr
    market_lines = market_context(provider, cfg, need_us, need_kr)

    hist = load_history()
    commentary, llm_used, cost = llm_section(symbols, market_lines, live, hist)

    warn = ("" if live else
            "\n> ## ⚠️ 라이브 데이터 수집 실패 — 아래 수치는 **합성 샘플 데이터** 기반입니다. "
            "실제 투자 참고 금지.\n")
    body = [f"# 🌅 모닝브리핑 — {today}", "",
            f"> 생성 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} · "
            f"데이터 {provider_name} · 해설 {llm_used or '모듈'}", warn,
            "## 🧭 종합 해설", "", commentary, "",
            "## 📊 시장", "", *market_lines, "",
            "## 📈 관심종목", ""]
    body += [fmt_symbol_section(d) for d in symbols]
    body += ["---",
             "> ⚠️ **면책**: 본 브리핑은 교육·연구 목적입니다. 제공되는 점수와 추천은 "
             "투자 자문이 아니며, 모든 투자 판단과 결과의 책임은 사용자 본인에게 있습니다."]

    out_dir = ROOT / "reports"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"모닝브리핑_{today}.md"
    out_path.write_text("\n".join(body), encoding="utf-8")

    hist["runs"].append({
        "date": today, "ts": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "provider": provider_name, "live": live, "symbols": len(symbols),
        "failed": sum(1 for d in symbols if "error" in d),
        "llm": llm_used, "cost_krw": cost,
        "elapsed_sec": round(time.time() - START, 1),
    })
    hist["runs"] = hist["runs"][-365:]
    HISTORY.write_text(json.dumps(hist, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"OK: {out_path} (elapsed {time.time() - START:.1f}s, llm={llm_used}, "
          f"cost={cost} KRW)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        log_error(traceback.format_exc().replace("\n", " | "))
        print("FAILED - see error.log")
        sys.exit(1)
