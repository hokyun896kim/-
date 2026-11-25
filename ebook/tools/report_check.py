# -*- coding: utf-8 -*-
"""5권 11·12장 검증 — 리포트 목록(CSV) + 시세(Yahoo Finance)로 목표주가 도달률과 상향 리포트 뒤 수익률을 계산한다.
사용: cd ebook && python3 tools/report_check.py plans/book5_리포트목록.csv
입력 CSV 열: 발간일(YYYY-MM-DD), 종목코드(6자리), 종목명, 증권사, 투자의견, 목표주가, 직전목표주가(없으면 빈칸)
원칙(본문 11·12장과 같다):
  · 도달: 발간 다음 거래일부터 252거래일 안 장중 고가 ≥ 발간 시점 목표주가. 목표주가는 고정
  · 시세가 없거나 기간 중 끊긴 종목(상장폐지·거래정지 의심)은 빼지 않고 미도달로 센다 — 따로 표시해 공시로 확인
  · 상향(목표주가 > 직전목표주가): 다음 거래일 시가 진입, 5·20·60거래일 뒤 종가 수익률
  · 같은 종목·같은 주의 상향은 첫 리포트만
  · 비교군: OpenDART 상장사 목록에서 고정 시드로 뽑은 무작위 종목 풀, 같은 진입일·같은 방식
  · 주가는 받은 파일 값만 쓴다(지어내지 않음). 원시 시세는 build/prices/ 캐시(git 제외)
산출: plans/book5_검증메모.md (요약 + 건별 표)"""
import csv, pathlib, random, sys, time, datetime as dt
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
PX = ROOT / "build" / "prices"; PX.mkdir(parents=True, exist_ok=True)
POOL_N, SEED, HORIZONS, WINDOW = 120, 5, (5, 20, 60), 252

def prices(code):
    """일별 시세(수정주가 아님: 시가·고가·종가 원값) — .KS 먼저, 없으면 .KQ. 캐시 사용."""
    f = PX / f"{code}.csv"
    if f.exists():
        d = pd.read_csv(f, index_col=0, parse_dates=True)
        return d if len(d) else None
    import yfinance as yf
    for suf in (".KS", ".KQ"):
        for k in range(3):
            try:
                d = yf.download(code + suf, start="2015-01-01", progress=False, auto_adjust=False)
                break
            except Exception:
                time.sleep(5 * (k + 1)); d = None
        if d is not None and len(d):
            d.columns = [c[0] if isinstance(c, tuple) else c for c in d.columns]
            d = d[["Open", "High", "Low", "Close"]].dropna()
            d.to_csv(f); time.sleep(0.6)
            return d
    pd.DataFrame(columns=["Open", "High", "Low", "Close"]).to_csv(f)
    return None

def after(d, day):
    """발간일 다음 거래일부터의 시세."""
    return d[d.index > pd.Timestamp(day)]

def reach(row):
    d = prices(row["종목코드"]); tp = float(row["목표주가"])
    if d is None: return dict(판정="시세 없음(상장폐지 등 확인)", 도달=False)
    w = after(d, row["발간일"]).iloc[:WINDOW]
    if w.empty: return dict(판정="시세 없음(발간 뒤)", 도달=False)
    hit = w[w["High"] >= tp]
    if len(hit): return dict(판정="도달", 도달=True, 일수=int(w.index.get_loc(hit.index[0])) + 1)
    cut = len(w) < WINDOW and w.index[-1] < pd.Timestamp.today() - pd.Timedelta(days=30)
    gap = (w["Close"].iloc[-1] - tp) / tp
    return dict(판정="미도달" + ("(시세 끊김)" if cut else ""), 도달=False, 괴리율=gap, 기간=len(w))

def ret(d, day, h):
    w = after(d, day)
    if len(w) <= h: return None
    return w["Close"].iloc[h] / w["Open"].iloc[0] - 1

def pool():
    sys.path.insert(0, str(ROOT / "tools")); import opendart
    codes = sorted({s for _, _, s in opendart.corp_codes() if s.strip()})
    rnd = random.Random(SEED); return rnd.sample(codes, POOL_N)

def main(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    out = [dict(r, **reach(r)) for r in rows]
    n = len(out); hit = [o for o in out if o["도달"]]
    miss_gap = [o["괴리율"] for o in out if "괴리율" in o]
    nodata = [o for o in out if o["판정"].startswith("시세 없음") or "끊김" in o["판정"]]
    # 상향 이벤트
    ups, seen = [], set()
    for r in sorted(rows, key=lambda r: r["발간일"]):
        p0 = r.get("직전목표주가", "").replace(",", "").strip()
        if not p0 or float(r["목표주가"]) <= float(p0): continue
        wk = (r["종목코드"], dt.date.fromisoformat(r["발간일"]).isocalendar()[:2])
        if wk in seen: continue
        seen.add(wk); ups.append(r)
    P = [c for c in pool() if prices(c) is not None]
    ev = []
    for r in ups:
        d = prices(r["종목코드"])
        if d is None: continue
        e = {"발간일": r["발간일"], "종목": r["종목명"]}
        for h in HORIZONS:
            a = ret(d, r["발간일"], h)
            b = [x for x in (ret(prices(c), r["발간일"], h) for c in P) if x is not None]
            e[h] = (a, sum(b) / len(b) if b else None)
        ev.append(e)
    md = [f"# 5권 11·12장 검증 메모 (자동 생성 {dt.date.today()})", "",
          f"- 입력: `{path}` {n}건 · 시세: Yahoo Finance(원가격) · 비교 풀: OpenDART 상장사 {POOL_N}개(시드 {SEED}) 중 시세 있는 {len(P)}개", "",
          "## 11장 도달률", "",
          f"- 도달 {len(hit)} / {n} = {len(hit)/n:.1%}" if n else "- 표본 없음",
          f"- 시세 없음·끊김(빼지 않고 미도달) {len(nodata)}건 → 빼면 {len(hit)}/{n-len(nodata)} = {len(hit)/max(n-len(nodata),1):.1%}",
          f"- 평균 도달 일수 {sum(o['일수'] for o in hit)/len(hit):.0f}거래일" if hit else "- 도달 없음",
          f"- 미도달 평균 괴리율 {sum(miss_gap)/len(miss_gap):.1%}" if miss_gap else "", "",
          "## 12장 상향 리포트 뒤 수익률(다음 거래일 시가 진입)", "", f"- 상향 이벤트 {len(ev)}건(같은 종목·같은 주 중복 제거)", ""]
    for h in HORIZONS:
        pairs = [e[h] for e in ev if e[h][0] is not None and e[h][1] is not None]
        if pairs:
            a = sum(p[0] for p in pairs) / len(pairs); b = sum(p[1] for p in pairs) / len(pairs)
            win = sum(p[0] > p[1] for p in pairs) / len(pairs)
            md.append(f"- {h}거래일: 상향 {a:+.2%} / 무작위 {b:+.2%} / 초과 {a-b:+.2%}p / 무작위보다 나은 비율 {win:.0%} (n={len(pairs)})")
    md += ["", "## 건별(도달)", "", "| 발간일 | 종목 | 증권사 | 목표주가 | 판정 | 일수/괴리율 |", "|---|---|---|---|---|---|"]
    for o in out:
        extra = f"{o['일수']}일" if "일수" in o else (f"{o['괴리율']:.1%}" if "괴리율" in o else "")
        md.append(f"| {o['발간일']} | {o['종목명']} | {o['증권사']} | {o['목표주가']} | {o['판정']} | {extra} |")
    (ROOT / "plans" / "book5_검증메모.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md[:20]))

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "plans" / "book5_리포트목록.csv"))
