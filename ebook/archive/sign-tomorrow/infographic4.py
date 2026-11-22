# -*- coding: utf-8 -*-
"""
4권 『사인은 내일 할게요』 인포그래픽.
diagram-design(MIT) 원칙을 이식: 글자 대비 4.5:1 이상(자동 검사), 강조색은 그림당 1~2곳,
역할별 글자 크기 4단계(하한 40px = 신국판 118mm 폭에서 약 5.5pt), 막대 축은 0부터,
숫자는 계산으로 만들고 원고(source/book4.md)에 같은 값이 있는지 대조(데이터 계약).
산출: build/img/ig4_<장>.png (2400px 폭)
"""
import pathlib, cairosvg
from PIL import ImageFont

ROOT = pathlib.Path(__file__).resolve().parent
IMG = ROOT / "build" / "img"; IMG.mkdir(parents=True, exist_ok=True)
MD = (ROOT / "source" / "book4.md").read_text(encoding="utf-8")
SANS, SERIF = "Noto Sans CJK KR", "Noto Serif CJK KR"
FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"

# ── 색: 흰 종이 + 잉크 파랑 + 서명란 빨강(표지 방향). 글자용과 면용을 나눈다
PAPER, INK, BLUE, RED, RED_FILL = "#FFFFFF", "#1D1D1F", "#1F3F7A", "#B3261E", "#D64A3A"
MUTE, RULE, SOFT = "#5F5A52", "#D9D4CA", "#EEF1F7"
ROLE = {"title": 72, "head": 48, "body": 42, "note": 40}      # 이 네 크기만 쓴다

def _lum(h):
    c = [int(h[i:i+2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= .03928 else ((x + .055) / 1.055) ** 2.4 for x in c]
    return .2126 * c[0] + .7152 * c[1] + .0722 * c[2]

def contrast(a, b=PAPER):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + .05) / (lb + .05)

for _c in (INK, BLUE, RED, MUTE):                       # 글자색 대비 계약
    assert contrast(_c) >= 4.5, (_c, round(contrast(_c), 2))

def won(v):  return f"{round(v):,}원"
def man(v):  # 1,013,371 → 101만 3,400원 (원고 표기: 백 원 단위 반올림)
    v = round(v / 100) * 100; m, r = divmod(int(v), 10000)
    return f"{m}만 {r:,}원" if r else f"{m}만 원"

def must_be_in_md(*texts):
    """데이터 계약: 그림에 쓰는 숫자 문자열이 원고에 그대로 있어야 한다."""
    for t in texts: assert t in MD, f"원고에 없는 숫자: {t}"

def T(x, y, s, role, fill=INK, w=500, anchor="start", font=SANS):
    size = ROLE[role]
    s = str(s).replace("&", "&amp;").replace("<", "&lt;")
    return (f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" font-weight="{w}" '
            f'fill="{fill}" text-anchor="{anchor}">{s}</text>')

def width(s, role):
    return ImageFont.truetype(FONT_BOLD, ROLE[role], index=1).getlength(str(s))

def save(name, W, H, body):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
           f'<rect width="{W}" height="{H}" fill="{PAPER}"/>{"".join(body)}</svg>')
    out = IMG / f"{name}.png"
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(out), output_width=W, output_height=H)
    return out

def header(title, sub):
    return [T(80, 120, title, "title", INK, 700, font=SERIF), T(80, 190, sub, "body", MUTE)]

def pmt(P, annual, n):
    r = annual / 12
    return P * r / (1 - (1 + r) ** -n)

# ── 1장: 36칸 달력 — 하루 천 원이 107만 원이 되는 그림
def ch1():
    m, months, paid, pen = 29900, 36, 12, 0.30
    total, penalty = m * months, (months - paid) * m * pen
    must_be_in_md(won(total), won(penalty), "29,900원")
    W, H = 2400, 1080
    b = header("하루 천 원이 107만 원이 되기까지", "월 29,900원 × 36개월 약정 — 한 칸이 한 달")
    x0, y0, cell, gap = 80, 300, 160, 24
    for i in range(months):
        r, c = divmod(i, 12); x = x0 + c * (cell + gap); y = y0 + r * (cell + gap)
        if i < paid:   # 낸 달: 파랑 채움
            b.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="6" fill="{BLUE}"/>')
        else:          # 남은 달: 비움(흑백 인쇄에서도 구분)
            b.append(f'<rect x="{x+3}" y="{y+3}" width="{cell-6}" height="{cell-6}" rx="6" fill="none" stroke="{BLUE}" stroke-width="6"/>')
    yb = y0 + 3 * (cell + gap) + 24
    b.append(T(x0, yb + 40, f"12개월 낸 뒤 해지하면 — 남은 24칸의 30%를 위약금으로 (가정)", "body", MUTE))
    b.append(f'<path d="M80 {yb+96} H2320" stroke="{RULE}" stroke-width="3"/>')
    b.append(T(80, yb + 190, "총비용", "head", INK, 700))
    b.append(T(560, yb + 190, won(total), "head", BLUE, 700))
    b.append(T(1240, yb + 190, "12개월 뒤 위약금", "head", INK, 700))
    b.append(T(2320, yb + 190, won(penalty), "head", RED, 700, "end"))      # 강조 1곳
    return save("ig4_1", W, H, b)

# ── 2장: 시나리오별 월 상환액 + 감당선 (축 0부터)
def ch2():
    P, n, cap = 2e8, 360, 1_050_000
    rows = [("고정 4.5%", .045), ("변동 — 그대로 4.0%", .040), ("변동 — 1%p 오르면 5.0%", .050), ("변동 — 1%p 내리면 3.0%", .030)]
    vals = [(lbl, pmt(P, a, n)) for lbl, a in rows]
    must_be_in_md(*[man(v) for _, v in vals], "105만 원")
    W, H = 2400, 1240
    b = header("내 감당선을 먼저 긋는다", "대출 2억 원 · 30년 · 원리금균등 — 월 상환액(예시)")
    xl, xr, top, rowh = 760, 2200, 320, 190
    scale = (xr - xl) / 1_200_000
    for k in range(0, 1_200_001, 300_000):                       # 눈금(장식선)
        x = xl + k * scale
        b.append(f'<path d="M{x} {top-30} V{top+rowh*4-40}" stroke="{RULE}" stroke-width="2"/>')
        b.append(T(x, top + rowh * 4 + 20, f"{k//10000}만" if k else "0", "note", MUTE, 400, "middle"))
    xc = xl + cap * scale
    b.append(f'<path d="M{xc} {top-60} V{top+rowh*4-40}" stroke="{RED}" stroke-width="6" stroke-dasharray="18 12"/>')
    b.append(T(xc + 16, top - 40, "감당선 월 105만 원", "body", RED, 700))
    for i, (lbl, v) in enumerate(vals):          # 막대가 감당선 위를 덮도록 선을 먼저 그린다
        y = top + i * rowh; over = v > cap
        b.append(T(80, y + 72, lbl, "body", INK, 500))
        fill = RED_FILL if over else BLUE
        b.append(f'<rect x="{xl}" y="{y+20}" width="{v*scale:.0f}" height="80" fill="{fill}"/>')
        b.append(T(xl + v * scale - 24, y + 76, man(v), "body", PAPER, 700, "end"))   # 막대 안쪽, 감당선과 겹치지 않게
    b.append(T(80, H - 60, "금리가 처음부터 끝까지 그 수준이라고 단순화한 계산입니다.", "note", MUTE, 400))
    return save("ig4_2", W, H, b)

# ── 3장: 손익분기 — 누적 절감액이 갈아타기 비용을 넘는 달
def ch3():
    P, n, cost = 1.5e8, 240, 1_950_000
    old = pmt(P, .05, n)
    lines = [("4.2%로 갈아타면", old - pmt(P, .042, n), BLUE), ("4.6%로 갈아타면", old - pmt(P, .046, n), MUTE)]
    be = [cost / s for _, s, _ in lines]
    must_be_in_md("약 30개월", "약 59개월", "195만 원")
    assert round(be[0]) == 30 and round(be[1]) == 59
    W, H = 2400, 1300
    b = header("갈아탄 비용을 언제 회수할까", "남은 1억 5천만 원 · 20년 · 5.0%에서 갈아타기, 비용 195만 원(예시)")
    xl, xr, yb, yt, xmax, ymax = 300, 2240, 1080, 300, 72, 4_000_000
    sx, sy = (xr - xl) / xmax, (yb - yt) / ymax
    for k in range(0, ymax + 1, 1_000_000):
        y = yb - k * sy
        b.append(f'<path d="M{xl} {y} H{xr}" stroke="{RULE}" stroke-width="2"/>')
        b.append(T(xl - 24, y + 14, f"{k//10000}만" if k else "0", "note", MUTE, 400, "end"))
    for mth in range(0, xmax + 1, 12):
        b.append(T(xl + mth * sx, yb + 60, f"{mth}개월", "note", MUTE, 400, "middle"))
    yc = yb - cost * sy                                               # 비용 수평선
    b.append(f'<path d="M{xl} {yc} H{xr}" stroke="{INK}" stroke-width="5" stroke-dasharray="16 12"/>')
    b.append(T(xl + 24, yc - 24, "갈아타는 데 드는 돈 195만 원", "note", INK, 700))
    for (lbl, s, col), m0 in zip(lines, be):
        end = min(xmax, ymax / s)
        b.append(f'<path d="M{xl} {yb} L{xl+end*sx:.0f} {yb-s*end*sy:.0f}" stroke="{col}" stroke-width="8"/>')
        cx = xl + m0 * sx
        b.append(f'<circle cx="{cx:.0f}" cy="{yc:.0f}" r="14" fill="{col}"/>')
        b.append(f'<path d="M{cx:.0f} {yc+18:.0f} V{yb}" stroke="{col}" stroke-width="3" stroke-dasharray="6 8"/>')
    b.append(T(xl + be[0] * sx + 24, yc + 70, "4.2% → 약 30개월", "body", BLUE, 700))
    b.append(T(xl + be[1] * sx + 24, yc + 70, "4.6% → 약 59개월", "body", MUTE, 700))
    return save("ig4_3", W, H, b)

def build():
    return [ch1(), ch2(), ch3()]

if __name__ == "__main__":
    for p in build(): print(p)
