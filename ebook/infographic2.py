# -*- coding: utf-8 -*-
"""
2권 새 인포그래픽 — 표지(물음표 길)와 같은 결: 남색·주황 2색, 얇은 선, 편집 디자인.
① 장 머리 ‘경제 노선도’ 띠: 이 책의 역들을 한 줄로 잇고, 지금 장의 역에 불을 켠다.
② 장별 핵심 그림(시범: 3장 금리).
산출: build/img/route_{장}.png, ig2_*.png
"""
import pathlib, cairosvg

ROOT = pathlib.Path(__file__).resolve().parent
IMG = ROOT / "build" / "img"; IMG.mkdir(parents=True, exist_ok=True)
SANS, SERIF = "Noto Sans CJK KR", "Noto Serif CJK KR"
NAVY, ORANGE, PAPER, MUTE, LINE = "#22304D", "#D9542B", "#FBF9F4", "#8A8478", "#D8D1C3"

K = 1.3   # 쪽에서 5pt 밑으로 줄지 않도록 글자 전체 배율

def T(x, y, s, size, fill=NAVY, w=700, anchor="middle", font=SANS, ls=0, op=1):
    size = round(size * K)
    s = s.replace("&", "&amp;").replace("<", "&lt;")
    return (f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" font-weight="{w}" fill="{fill}" '
            f'text-anchor="{anchor}" letter-spacing="{ls}" opacity="{op}">{s}</text>')

def save(name, W, H, body):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
           f'<rect width="{W}" height="{H}" fill="{PAPER}"/>{"".join(body)}</svg>')
    out = IMG / f"{name}.png"
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(out), output_width=W, output_height=H)
    return out

# ── ① 경제 노선도 띠 ───────────────────────────────────────────
# (역 이름, 해당 장) — 뉴스가 내 계좌에 닿는 순서대로
STATIONS = [("유가·지정학", 8), ("물가", 5), ("고용", 6), ("중앙은행", 7), ("금리", 3),
            ("환율", 4), ("기업 실적", 9), ("내 계좌", None)]

def route(ch):
    W, H = 2400, 520
    b = [T(80, 92, "경제 노선도", 40, ORANGE, 800, "start", ls=3)]
    here = next((n for n, c in STATIONS if c == ch), None)
    if here: b.append(T(2320, 92, f"{ch}장 · {here}역", 40, NAVY, 700, "end"))
    b.append(f'<path d="M80 128 H2320" stroke="{LINE}" stroke-width="3"/>')
    y, x0, x1 = 300, 190, 2130
    step = (x1 - x0) / (len(STATIONS) - 1)
    b.append(f'<path d="M{x0} {y} H{x1}" stroke="{NAVY}" stroke-width="16" stroke-linecap="round"/>')
    b.append(f'<path d="M{x1} {y} H2290" stroke="{NAVY}" stroke-width="16" stroke-dasharray="4 26" stroke-linecap="round"/>')
    for i, (name, c) in enumerate(STATIONS):
        x = x0 + i * step
        last = c is None
        if c == ch:
            b.append(f'<circle cx="{x}" cy="{y}" r="44" fill="{ORANGE}" opacity=".18"/>')
            b.append(f'<circle cx="{x}" cy="{y}" r="28" fill="{ORANGE}"/>')
            b.append(f'<rect x="{x-92}" y="{y-118}" width="184" height="58" rx="29" fill="{ORANGE}"/>')
            b.append(T(x, y - 78, "지금 여기", 30, PAPER, 800))
            b.append(T(x, y + 92, name, 42, ORANGE, 800))
        elif last:
            b.append(f'<rect x="{x-30}" y="{y-30}" width="60" height="60" rx="10" fill="{NAVY}"/>')
            b.append(T(x, y + 92, name, 42, NAVY, 800))
        else:
            b.append(f'<circle cx="{x}" cy="{y}" r="24" fill="{PAPER}" stroke="{NAVY}" stroke-width="10"/>')
            b.append(T(x, y + 92, name, 38, NAVY, 600))
        if c and c != ch:
            b.append(T(x, y - 56, f"{c}장", 28, MUTE, 600))
    b.append(T(1200, 480, "뉴스는 출발역과 도착역만 말합니다. 이 책은 그 사이의 역을 내려 봅니다.", 30, MUTE, 500))
    return save(f"route_{ch}", W, H, b)

# ── ② 3장: 문자 한 통이 오기까지 ───────────────────────────────
def phone(x, y, w=250, h=430):
    return [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="36" fill="{PAPER}" stroke="{NAVY}" stroke-width="8"/>',
            f'<rect x="{x+w/2-34}" y="{y+18}" width="68" height="10" rx="5" fill="{NAVY}"/>',
            f'<rect x="{x+22}" y="{y+70}" width="{w-44}" height="150" rx="18" fill="{ORANGE}" opacity=".12"/>',
            T(x + 40, y + 112, "[은행] 대출", 26, ORANGE, 800, "start"),
            T(x + 40, y + 150, "적용금리가", 26, NAVY, 700, "start"),
            T(x + 40, y + 188, "변경됩니다", 26, NAVY, 700, "start"),
            f'<path d="M{x+40} {y+260} H{x+w-40} M{x+40} {y+296} H{x+w-80} M{x+40} {y+332} H{x+w-60}" '
            f'stroke="{LINE}" stroke-width="10" stroke-linecap="round"/>']

def ig_rate_flow():
    W, H = 2400, 1180
    b = [T(80, 120, "문자 한 통이 오기까지", 76, NAVY, 800, "start", font=SERIF),
         T(80, 190, "금리 뉴스가 내 통장에 도착하는 길", 38, MUTE, 500, "start")]
    # 역: 뉴스 → 시장금리 → 은행 대출금리 → (휴대폰)
    stops = [(250, "① 금리 뉴스", ["“기준금리 동결”", "“인하 신중론”"]),
             (760, "② 시장금리", ["은행의 조달 값", "이 움직인다"]),
             (1270, "③ 내 대출금리", ["변동금리라면", "주기마다 반영"])]
    y = 560
    b.append(f'<path d="M{stops[0][0]} {y} H1700" stroke="{NAVY}" stroke-width="14" stroke-linecap="round"/>')
    b.append(f'<path d="M1700 {y} l-34 -26 M1700 {y} l-34 26" stroke="{NAVY}" stroke-width="14" stroke-linecap="round"/>')
    for x, head, lines in stops:
        b.append(f'<circle cx="{x}" cy="{y}" r="30" fill="{PAPER}" stroke="{NAVY}" stroke-width="12"/>')
        b.append(T(x, y - 80, head, 44, NAVY, 800))
        for j, ln in enumerate(lines):
            b.append(T(x, y + 100 + j * 54, ln, 36, NAVY if j == 0 else MUTE, 600 if j == 0 else 500))
    b += phone(1790, 330)
    b.append(T(1915, 820, "④ 내 휴대폰", 44, ORANGE, 800))
    # 마지막 갈래: 매달 이자 → 생활비
    b.append(f'<path d="M80 930 H2320" stroke="{LINE}" stroke-width="3"/>')
    b.append(T(80, 1020, "⑤ 그다음", 40, ORANGE, 800, "start"))
    chain = ["이자 ↑", "쓸 돈 ↓", "외식·여행 조정", "“소비 둔화”"]
    xs = [610, 1050, 1560, 2080]
    for i, (x, s) in enumerate(zip(xs, chain)):
        b.append(T(x, 1022, s, 40, NAVY if i < 3 else MUTE, 700 if i < 3 else 500))
        if i < 3: b.append(T((x + xs[i+1]) / 2 + (60 if i == 2 else 0), 1022, "→", 40, ORANGE, 800))
    b.append(T(80, 1120, "뉴스는 ①과 ⑤만 말합니다.", 34, MUTE, 500, "start"))
    return save("ig2_3a", W, H, b)

# ── ③ 3장: 같은 금리 상승, 다른 얼굴 ──────────────────────────
def person(x, y, col):
    return [f'<circle cx="{x}" cy="{y}" r="44" fill="{PAPER}" stroke="{col}" stroke-width="9"/>',
            f'<path d="M{x-80} {y+170} Q{x-80} {y+66} {x} {y+66} Q{x+80} {y+66} {x+80} {y+170}" '
            f'fill="{PAPER}" stroke="{col}" stroke-width="9" stroke-linejoin="round"/>']

def item(kind, x, y, col):
    """사람 옆 작은 소품: doc(대출 서류)·coin(예금)·house(집)·shop(가게)."""
    sw = f'fill="{PAPER}" stroke="{col}" stroke-width="7" stroke-linejoin="round"'
    if kind == "doc":
        return [f'<rect x="{x-38}" y="{y-50}" width="76" height="100" rx="8" {sw}/>', T(x, y + 16, "%", 44, col, 800)]
    if kind == "coin":
        return [f'<ellipse cx="{x}" cy="{y+30-i*24}" rx="44" ry="15" {sw}/>' for i in range(4)]
    if kind == "house":
        return [f'<path d="M{x-48} {y} L{x} {y-48} L{x+48} {y} V{y+48} H{x-48} Z" {sw}/>',
                f'<rect x="{x-12}" y="{y+16}" width="24" height="32" fill="{col}"/>']
    return [f'<path d="M{x-52} {y-20} H{x+52} L{x+40} {y-50} H{x-40} Z" {sw}/>',
            f'<rect x="{x-44}" y="{y-20}" width="88" height="68" {sw}/>',
            f'<rect x="{x-14}" y="{y+12}" width="28" height="36" fill="{col}"/>']

def ig_rate_faces():
    W, H = 2400, 1240
    b = [T(80, 120, "같은 금리 상승, 다른 얼굴", 76, NAVY, 800, "start", font=SERIF)]
    # 위: 금리 ↑ 막대
    b.append(f'<rect x="980" y="190" width="440" height="110" rx="55" fill="{NAVY}"/>')
    b.append(T(1200, 264, "금리 ↑", 56, PAPER, 800))
    who = [(330, "변동금리 대출자", "다음 달 이자 ↑", ORANGE, "부담", "doc"),
           (910, "예금·적금 가입자", "받는 이자 ↑", NAVY, "기회", "coin"),
           (1490, "집을 고민하는 사람", "월 상환액 다시 계산", ORANGE, "부담", "house"),
           (2070, "동네 가게", "손님 지갑이 닫힘", ORANGE, "부담", "shop")]
    for x, name, eff, col, tag, kind in who:
        b.append(f'<path d="M1200 300 C1200 380 {x} 360 {x} 450" fill="none" stroke="{LINE}" stroke-width="6"/>')
        b += person(x - 40, 540, col)
        b += item(kind, x + 110, 640, col)
        b.append(f'<rect x="{x-70}" y="760" width="140" height="58" rx="29" fill="{col}"/>')
        b.append(T(x, 800, tag, 32, PAPER, 800))
        b.append(T(x, 890, name, 42, NAVY, 800))
        b.append(T(x, 948, eff, 36, MUTE, 500))
    b.append(f'<path d="M80 1050 H2320" stroke="{LINE}" stroke-width="3"/>')
    b.append(T(1200, 1150, "“누구에게 좋은가?  누구에게 부담인가?  나는 어느 쪽에 가까운가?”", 46, NAVY, 700, font=SERIF))
    return save("ig2_3b", W, H, b)

# ── ④ 장별 사양(JSON) → 그림: chain / people ─────────────────────
def chain_fig(name, sp):
    W, H = 2400, 1180
    st = sp["steps"][:4]; n = len(st)
    b = [T(80, 120, sp["title"], 76, NAVY, 800, "start", font=SERIF)]
    if sp.get("subtitle"): b.append(T(80, 190, sp["subtitle"], 38, MUTE, 500, "start"))
    y = 520; x0, x1 = 330, 2070
    xs = [x0 + i * (x1 - x0) / (n - 1) for i in range(n)] if n > 1 else [1200]
    b.append(f'<path d="M{xs[0]} {y} H2290" stroke="{NAVY}" stroke-width="14" stroke-linecap="round"/>')
    b.append(f'<path d="M2290 {y} l-34 -26 M2290 {y} l-34 26" stroke="{NAVY}" stroke-width="14" stroke-linecap="round"/>')
    for i, (x, it) in enumerate(zip(xs, st)):
        last = i == n - 1
        col = ORANGE if last else NAVY
        b.append(f'<circle cx="{x}" cy="{y}" r="30" fill="{ORANGE if last else PAPER}" stroke="{col}" stroke-width="12"/>')
        b.append(T(x, y - 80, it["head"], 44, col, 800))
        if it.get("l1"): b.append(T(x, y + 100, it["l1"], 36, NAVY, 600))
        if it.get("l2"): b.append(T(x, y + 154, it["l2"], 36, MUTE, 500))
    tail = sp.get("tail") or []
    b.append(f'<path d="M80 860 H2320" stroke="{LINE}" stroke-width="3"/>')
    if tail:
        from PIL import ImageFont
        b.append(T(80, 950, sp.get("tail_label", "그다음"), 40, ORANGE, 800, "start"))
        fs = 40
        font = lambda z: ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", round(z * K), index=1)
        x_lo, x_hi, gap = 640, 2330, 70          # 화살표(→) 한 칸 폭 = gap
        while True:
            ws = [font(fs).getlength(t) for t in tail]
            total = sum(ws) + gap * (len(tail) - 1) * 2
            if total <= x_hi - x_lo or fs <= 30: break
            fs -= 2
        x = x_lo + max(0, (x_hi - x_lo - total) / 2)
        for i, (t, w) in enumerate(zip(tail, ws)):
            last = i == len(tail) - 1
            b.append(T(x + w / 2, 952, t, fs, MUTE if last else NAVY, 500 if last else 700))
            x += w
            if not last:
                b.append(T(x + gap, 952, "→", fs, ORANGE, 800)); x += gap * 2
    if sp.get("foot"): b.append(T(80, 1090, sp["foot"], 34, MUTE, 500, "start"))
    return save(name, W, H, b)

def people_fig(name, sp):
    W, H = 2400, 1240
    items = sp["items"][:4]; n = len(items)
    b = [T(80, 120, sp["title"], 76, NAVY, 800, "start", font=SERIF)]
    b.append(f'<rect x="960" y="190" width="480" height="110" rx="55" fill="{NAVY}"/>')
    b.append(T(1200, 264, sp["center"], 56, PAPER, 800))
    xs = [1200] if n == 1 else [330 + i * (2070 - 330) / (n - 1) for i in range(n)]
    for x, it in zip(xs, items):
        col = NAVY if it.get("tag") in ("기회", "기대") else ORANGE
        b.append(f'<path d="M1200 300 C1200 380 {x} 360 {x} 450" fill="none" stroke="{LINE}" stroke-width="6"/>')
        b += person(x - 40, 540, col)
        b += item(it.get("icon", "doc"), x + 110, 640, col)
        b.append(f'<rect x="{x-70}" y="760" width="140" height="58" rx="29" fill="{col}"/>')
        b.append(T(x, 800, it.get("tag", ""), 32, PAPER, 800))
        b.append(T(x, 890, it["who"], 42, NAVY, 800))
        b.append(T(x, 948, it["effect"], 36, MUTE, 500))
    b.append(f'<path d="M80 1050 H2320" stroke="{LINE}" stroke-width="3"/>')
    if sp.get("foot"): b.append(T(1200, 1150, sp["foot"], 46, NAVY, 700, font=SERIF))
    return save(name, W, H, b)

def from_json(n, path):
    import json
    sp = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    f = chain_fig if sp["type"] == "chain" else people_fig
    return f(f"ig2_{n}", sp)

def build():
    out = [route(3), ig_rate_flow(), ig_rate_faces()]
    for c in (4, 5, 6, 7, 8, 9): out.append(route(c))
    for f in sorted((ROOT / "fig2_specs").glob("ch*.json")):
        out.append(from_json(int(f.stem[2:]), f))
    return out

if __name__ == "__main__":
    for p in build(): print(p)
