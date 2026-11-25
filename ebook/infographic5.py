# -*- coding: utf-8 -*-
"""
5권 『매수 의견만 있는 나라』 본문 그림 — 세 갈래로 그린다.
  · 인포그래픽(chart): 숫자를 그린 그림. 정밀한 선, 축은 0부터(막대), 숫자는 계산으로 만들고 원고와 대조
  · 아티팩트(artifact): 리포트 첫 장·AI 대화창처럼 '화면/문서' 자체를 그린 그림. 표지와 같은 터미널 언어
  · 드로잉(sketch): 개념 그림. 손으로 그은 듯 살짝 흔들리는 선(결정적 난수) — 데이터 그림에는 쓰지 않는다
규칙(design.md): 글자 대비 4.5:1·선 3:1 자동 검사, 강조색(신호 빨강)은 그림당 1~2곳, 글자 크기 역할 4단계,
                 사선 연결선·그림자·글로우 금지, 그림의 숫자 문자열은 source/book5.md에 있어야 한다(must_be_in_md).
산출: build/img/ig5_<id>.png (폭 2400px = 본문 118mm)
"""
import math, pathlib, random, re, cairosvg
from PIL import ImageFont

ROOT = pathlib.Path(__file__).resolve().parent
IMG = ROOT / "build" / "img"; IMG.mkdir(parents=True, exist_ok=True)
MD = (ROOT / "source" / "book5.md").read_text(encoding="utf-8")
SANS, MONO = "Noto Sans CJK KR", "JetBrains Mono"
F_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"

# ── 색: 표지와 같은 값. 빨강은 글자용(어두운)과 면·선용을 나눈다
PAPER, INK, SUB, MUTE, RULE, SOFT = "#FFFFFF", "#0D1117", "#3F4955", "#5B6572", "#D5DAE1", "#F2F4F7"
SIG, SIG_T, SIG_SOFT = "#FF4B3E", "#C42B20", "#FFE3E0"          # 면·선 / 글자 / 옅은 면
SCR, SCR2, SCR_EDGE, SCR_T, SCR_SUB, SCR_DIM = "#0D1117", "#151B23", "#2A323D", "#EEF1F5", "#AEB7C2", "#6F7A87"
ROLE = {"title": 64, "head": 48, "body": 42, "note": 40}

def _lum(h):
    c = [int(h[i:i+2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= .03928 else ((x + .055) / 1.055) ** 2.4 for x in c]
    return .2126 * c[0] + .7152 * c[1] + .0722 * c[2]
def contrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True); return (la + .05) / (lb + .05)
for _c in (INK, SUB, MUTE, SIG_T): assert contrast(_c, PAPER) >= 4.5, _c          # 종이 위 글자
for _c in (SCR_T, SCR_SUB, SIG): assert contrast(_c, SCR) >= 4.5, _c              # 화면 위 글자
assert contrast(SIG, PAPER) >= 3, "선·면 대비"
assert contrast(SCR_DIM, SCR) >= 3

def must_be_in_md(*texts):
    for s in texts: assert s in MD, f"원고에 없는 숫자/문구: {s}"

def esc(s): return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
_HAN = re.compile(r"[\uac00-\ud7a3\u3131-\u318e]")
def T(x, y, s, role="body", fill=INK, w=500, anchor="start", font=SANS, size=None, ls=0):
    if font == MONO and _HAN.search(str(s)): font = SANS          # 고정폭 글꼴엔 한글이 없다 → 한글 섞이면 고딕
    return (f'<text x="{x:.0f}" y="{y:.0f}" font-family="{font}" font-size="{size or ROLE[role]}" font-weight="{w}" '
            f'fill="{fill}" text-anchor="{anchor}" letter-spacing="{ls}">{esc(s)}</text>')
def tw(s, role="body", size=None): return ImageFont.truetype(F_BOLD, size or ROLE[role], index=1).getlength(str(s))
def R(x, y, w, h, fill="none", stroke=None, sw=3, rx=0):
    st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    return f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" rx="{rx}" fill="{fill}"{st}/>'
def L(x1, y1, x2, y2, c=INK, sw=3, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<path d="M{x1:.0f} {y1:.0f} L{x2:.0f} {y2:.0f}" stroke="{c}" stroke-width="{sw}" fill="none"{d}/>'

# ── 드로잉: 손으로 그은 듯한 선(두 번 겹쳐 긋고 끝을 살짝 흔든다). 결정적 난수
_rnd = random.Random(55)
def _j(a=5): return _rnd.uniform(-a, a)
def sline(x1, y1, x2, y2, c=INK, sw=4):
    out = []
    for k in range(2):
        mx, my = (x1 + x2) / 2 + _j(6), (y1 + y2) / 2 + _j(6)
        out.append(f'<path d="M{x1+_j():.1f} {y1+_j():.1f} Q{mx:.1f} {my:.1f} {x2+_j():.1f} {y2+_j():.1f}" '
                   f'stroke="{c}" stroke-width="{sw if k == 0 else sw*0.6:.1f}" fill="none" stroke-linecap="round" opacity="{1 if k == 0 else .7}"/>')
    return "".join(out)
def sbox(x, y, w, h, c=INK, fill=None, sw=4):
    out = [f'<path d="M{x+_j(3):.1f} {y+_j(3):.1f} L{x+w+_j(3):.1f} {y+_j(3):.1f} L{x+w+_j(3):.1f} {y+h+_j(3):.1f} L{x+_j(3):.1f} {y+h+_j(3):.1f} Z" fill="{fill}" stroke="none"/>'] if fill else []
    out += [sline(x, y, x + w, y, c, sw), sline(x + w, y, x + w, y + h, c, sw), sline(x + w, y + h, x, y + h, c, sw), sline(x, y + h, x, y, c, sw)]
    return "".join(out)
def sarrow(x1, y1, x2, y2, c=INK, sw=4):
    a = math.atan2(y2 - y1, x2 - x1); h = 26
    p1 = (x2 - h * math.cos(a - .45), y2 - h * math.sin(a - .45)); p2 = (x2 - h * math.cos(a + .45), y2 - h * math.sin(a + .45))
    return sline(x1, y1, x2, y2, c, sw) + sline(*p1, x2, y2, c, sw) + sline(*p2, x2, y2, c, sw)
def scircle(cx, cy, r, c=SIG, sw=5):
    pts = [(cx + (r + _j(4)) * math.cos(t / 20 * 2 * math.pi + .3), cy + (r + _j(4)) * math.sin(t / 20 * 2 * math.pi + .3)) for t in range(22)]
    return f'<path d="M{" L".join(f"{x:.1f} {y:.1f}" for x, y in pts)}" stroke="{c}" stroke-width="{sw}" fill="none" stroke-linecap="round"/>'

def badge(n, x, y, r=34):   # 번호 동그라미(아티팩트 주석)
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{SIG}"/>' + T(x, y + 15, n, size=42, fill="#FFFFFF", w=800, anchor="middle", font=MONO)

def save(name, W, H, body, bg=PAPER):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
           f'<rect width="{W}" height="{H}" fill="{bg}"/>{"".join(body)}</svg>')
    out = IMG / f"ig5_{name}.png"
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(out), output_width=W, output_height=H)
    return out

def head(b, kind, title, y=96):
    b.append(T(80, y, kind, size=34, fill=SIG_T, w=700, font=MONO, ls=6))
    b.append(T(80, y + 84, title, "title", INK, 800))
    b.append(L(80, y + 124, 2320, y + 124, RULE, 3))
    return y + 210

# ───────────────────────── 프롤로그 ─────────────────────────
def fig_p1():
    """주가가 먼저, 목표주가가 뒤에 — 가상의 B사 한 달(22거래일)."""
    must_be_in_md("6만 3,000원", "7만 9,000원", "8만 원", "10만 원")
    W, H = 2400, 1300; b = []
    y0 = head(b, "CHART · 가상의 B사", "주가가 먼저 오르고, 목표주가가 뒤따라 오른다")
    n = 22; rnd = random.Random(3)
    px = [63000]
    for i in range(1, n):
        target = 63000 + (79000 - 63000) * (i / (n - 1)) ** 1.15
        px.append(target + rnd.uniform(-900, 900) if i < n - 1 else 79000)
    gx0, gx1, gy0, gy1 = 260, 2000, y0 + 40, 1120
    lo, hi = 60000, 104000
    X = lambda i: gx0 + (gx1 - gx0) * i / (n - 1)
    Y = lambda v: gy1 - (gy1 - gy0) * (v - lo) / (hi - lo)
    for v in (60000, 70000, 80000, 90000, 100000):
        b.append(L(gx0, Y(v), gx1 + 40, Y(v), RULE, 2))
        b.append(T(gx0 - 24, Y(v) + 14, f"{v:,}", size=40, fill=MUTE, anchor="end", font=MONO))
    # 목표주가(계단): 마지막 날 전까지 8만, 알림 날 10만
    b.append(f'<path d="M{X(0):.0f} {Y(80000):.0f} H{X(n-1):.0f} V{Y(100000):.0f} H{gx1+40:.0f}" stroke="{SIG}" stroke-width="6" fill="none" stroke-dasharray="18 12"/>')
    b.append(T(X(0), Y(80000) - 22, "목표주가 8만 원", fill=SIG_T, w=700))
    b.append(T(X(n - 1) - 20, Y(100000) - 24, "알림: 10만 원으로 상향", fill=SIG_T, w=800, anchor="end"))
    # 주가(실선)
    b.append('<path d="M' + " L".join(f"{X(i):.0f} {Y(v):.0f}" for i, v in enumerate(px)) + f'" stroke="{INK}" stroke-width="7" fill="none" stroke-linejoin="round"/>')
    b.append(f'<circle cx="{X(0):.0f}" cy="{Y(63000):.0f}" r="12" fill="{INK}"/>' + T(X(0) + 26, Y(63000) + 60, "한 달 전 6만 3,000원", w=700))
    b.append(f'<circle cx="{X(n-1):.0f}" cy="{Y(79000):.0f}" r="12" fill="{INK}"/>' + T(X(n - 1) + 30, Y(79000) + 14, "7만 9,000원", w=800))
    b.append(T(gx0, 1200, "가상의 예시 · 주가는 설명을 위해 만든 값", "note", MUTE))
    return save("p1", W, H, b)

# ───────────────────────── 1장 ─────────────────────────
def fig_1a():
    """31곳 중 28곳 매도 0% — 칸 그림 + 최고 매도 비율 비교 막대(보도 기준)."""
    must_be_in_md("31곳", "28곳", "1.3%", "21.9%")
    W, H = 2400, 1100; b = []
    y0 = head(b, "CHART · 보도 기준, 2025년 말", "국내 증권사 31곳 가운데 28곳은 매도 의견 0%")
    s, g = 104, 18
    for i in range(31):
        r, c = divmod(i, 8); x, y = 80 + c * (s + g), y0 + 20 + r * (s + g)
        sell = i >= 28
        b.append(R(x, y, s, s, SIG if sell else SOFT, None if sell else RULE, 3))
        b.append(T(x + s / 2, y + s / 2 + 14, "매도" if sell else "0%", size=36, fill="#FFFFFF" if sell else MUTE, w=700, anchor="middle"))
    lx = 80; ly = y0 + 20 + 4 * (s + g) + 60
    b.append(R(lx, ly - 34, 40, 40, SOFT, RULE, 3) + T(lx + 56, ly, "매도 의견 0%", "note", SUB))
    b.append(R(lx + 400, ly - 34, 40, 40, SIG) + T(lx + 456, ly, "매도 의견을 낸 3곳", "note", SUB))
    # 오른쪽: 최고 매도 비율 비교(축 0부터)
    bx0, bx1 = 1260, 2280
    b.append(T(bx0, y0 + 40, "가장 높은 매도 비율", "head", INK, 800))
    mx = 25.0
    for k, (lab, v, col) in enumerate([("국내 증권사", 1.3, SIG), ("외국계 서울지점", 21.9, INK)]):
        y = y0 + 150 + k * 210
        b.append(T(bx0, y, lab, "body", SUB, 700))
        b.append(R(bx0, y + 30, (bx1 - bx0) * v / mx, 80, col))
        b.append(T(bx0 + (bx1 - bx0) * v / mx + 24, y + 92, f"{v}%", size=56, fill=SIG_T if col == SIG else INK, w=800, font=MONO))
    b.append(L(bx0, y0 + 160, bx0, y0 + 520, INK, 4))
    b.append(T(80, H - 50, "출처: 금융투자협회 집계를 인용한 2026년 3월 보도. 원자료 대조 전", "note", MUTE))
    return save("1a", W, H, b)

def fig_1b():
    """매도가 드문 이유 — 애널리스트를 둘러싼 세 방향의 압력(드로잉)."""
    W, H = 2400, 1500; b = []
    y0 = head(b, "DRAWING", "매도 대신 다른 길을 고르게 만드는 세 방향")
    cx, cy, bw, bh = 1200, y0 + 520, 560, 170
    b.append(sbox(cx - bw / 2, cy - bh / 2, bw, bh, INK, SOFT, 5))
    b.append(T(cx, cy + 16, "애널리스트", "head", INK, 800, "middle"))
    boxes = [(80, y0 + 40, "분석 대상 회사", "탐방·IR·설명회 접근"),
             (1720, y0 + 40, "같은 증권사 법인영업", "기관투자자 고객"),
             (80, y0 + 740, "같은 증권사 기업금융", "상장·증자·채권 발행")]
    for x, y, t1, t2 in boxes:
        b.append(sbox(x, y, 600, 190, SUB, None, 4))
        b.append(T(x + 300, y + 82, t1, "body", INK, 800, "middle"))
        b.append(T(x + 300, y + 142, t2, "note", MUTE, 500, "middle"))
    b.append(sarrow(680, y0 + 170, cx - bw / 2 - 20, cy - 40, SUB))
    b.append(sarrow(1720, y0 + 170, cx + bw / 2 + 20, cy - 40, SUB))
    b.append(sarrow(680, y0 + 800, cx - bw / 2 - 20, cy + 50, SUB))
    # 결과: 매도 대신 고르는 길
    ox, oy = 1380, y0 + 760
    b.append(sarrow(cx + 80, cy + bh / 2 + 10, ox + 60, oy - 10, SIG, 5))
    b.append(sbox(ox, oy, 940, 330, SIG, SIG_SOFT, 5))
    b.append(T(ox + 50, oy + 80, "매도 대신", "body", SIG_T, 800))
    for k, s in enumerate(["의견을 '중립'으로", "목표주가를 빼고", "리포트를 조용히 멈춘다"]):
        b.append(T(ox + 50, oy + 160 + k * 62, f"· {s}", "body", INK, 700))
    return save("1b", W, H, b)

# ───────────────────────── 2장 ─────────────────────────
def fig_2a():
    """리포트 첫 장 해부 — 가상의 B사 리포트(아티팩트) + 번호 주석."""
    must_be_in_md("100,000원", "79,000원", "26.6%", "2조 2,120억 원", "10,000", "11,500", "13,000", "1,850", "5,000")
    W, H = 2400, 2200; b = []
    y0 = head(b, "ARTIFACT · 가상의 리포트", "리포트 한 편은 다섯 부분으로 읽는다")
    px, py, pw = 80, y0 + 20, 1360; ph = H - py - 140
    b.append(R(px, py, pw, ph, "#FFFFFF", INK, 4))
    b.append(R(px, py, pw, 90, SCR))
    b.append(T(px + 40, py + 60, "○○증권 리서치센터 · 기업분석", size=36, fill=SCR_T, w=700))
    b.append(T(px + pw - 40, py + 60, "B사", size=36, fill=SCR_SUB, w=700, anchor="end"))
    # ① 다섯 칸 상자
    bx, by = px + 880, py + 130
    rows = [("투자의견", "매수(유지)"), ("목표주가", "100,000원(상향)"), ("현재주가", "79,000원"), ("상승여력", "26.6%"), ("시가총액", "2조 2,120억 원")]
    b.append(R(bx, by, 440, 52 * 5 + 20, SOFT, RULE, 2))
    for k, (a_, v) in enumerate(rows):
        yy = by + 50 + k * 52
        b.append(T(bx + 20, yy, a_, size=30, fill=MUTE, w=500))
        b.append(T(bx + 420, yy, v, size=30, fill=SIG_T if "상향" in v else INK, w=800, anchor="end"))
    # ② 제목 + 요약 세 줄
    b.append(T(px + 40, py + 190, "신규 고객사, 내년이 진짜다", size=52, fill=INK, w=900))
    for k, s in enumerate(["3분기 영업이익 410억 원, 컨센서스 상회", "2027년 매출 13% 성장 전망", "산정 기준 2027년으로 변경, 목표주가 상향"]):
        b.append(T(px + 40, py + 270 + k * 56, f"· {s}", size=32, fill=SUB, w=500))
    for k, w_ in enumerate([780, 800, 760, 790, 700]):
        b.append(R(px + 40, py + 470 + k * 34, w_, 12, RULE, rx=6))
    # ③ 추정표
    ty = py + 700
    b.append(T(px + 40, ty, "실적 추정 (억 원)", size=34, fill=INK, w=800))
    cols = ["", "2025A", "2026E", "2027E"]; data = [("매출액", "10,000", "11,500", "13,000"), ("영업이익", "1,200", "1,500", "1,850"), ("EPS(원)", "3,214", "4,000", "5,000")]
    b.append(R(px + 40, ty + 24, pw - 80, 56, SCR))
    for c, s in enumerate(cols):
        b.append(T(px + 60 + c * 320 + (0 if c == 0 else 260), ty + 64, s, size=30, fill=SCR_T, w=700, anchor="start" if c == 0 else "end", font=MONO))
    for r_, row in enumerate(data):
        yy = ty + 130 + r_ * 60
        for c, s in enumerate(row):
            b.append(T(px + 60 + c * 320 + (0 if c == 0 else 260), yy, s, size=30, fill=INK, w=500 if c == 0 else 600, anchor="start" if c == 0 else "end", font=SANS if c == 0 else MONO))
        b.append(L(px + 40, yy + 20, px + pw - 40, yy + 20, RULE, 2))
    # ④ 밸류에이션 한 줄
    vy = ty + 380
    b.append(T(px + 40, vy, "밸류에이션", size=34, fill=INK, w=800))
    b.append(R(px + 40, vy + 24, pw - 80, 90, SOFT, RULE, 2))
    b.append(T(px + 70, vy + 84, "목표주가 100,000원 = 2027E EPS 5,000원 × 목표 PER 20배", size=34, fill=INK, w=700))
    for k, w_ in enumerate([1180, 1120, 1200, 900]):
        b.append(R(px + 40, vy + 160 + k * 34, w_, 12, RULE, rx=6))
    # ⑤ 고지문(깨알)
    fy = py + ph - 330
    b.append(L(px + 40, fy - 30, px + pw - 40, fy - 30, INK, 2))
    b.append(T(px + 40, fy + 10, "투자등급 비율 · 목표주가 변동 내역과 괴리율 · 이해관계 고지", size=28, fill=MUTE, w=700))
    for k in range(6):
        b.append(R(px + 40, fy + 50 + k * 30, pw - 80 - (k % 3) * 120, 9, RULE, rx=4))
    # 주석: 번호와 오른쪽 설명(곧은 선만)
    notes = [("1", py + 150, "위쪽 다섯 칸", "숫자보다 괄호(유지·상향·하향)"),
             ("2", py + 360, "요약 세 줄", "사실 · 전망 · 계산으로 나눈다"),
             ("3", ty + 160, "실적 추정표", "A(실제)와 E(추정)를 가른다"),
             ("4", vy + 70, "밸류에이션 한 줄", "무엇 × 몇 배 — 결론의 전부"),
             ("5", fy + 60, "맨 뒤 고지문", "등급 비율 · 괴리율 · 이해관계")]
    for n_, yy, t1, t2 in notes:
        b.append(L(px + pw + 8, yy, 1560, yy, SIG, 4))
        b.append(badge(n_, 1600, yy))
        b.append(T(1660, yy - 4, t1, "body", INK, 800))
        b.append(T(1660, yy + 50, t2, "note", MUTE, 500))
    b.append(T(80, H - 60, "가상의 예시 · 증권사·숫자 모두 설명을 위해 만든 값", "note", MUTE))
    return save("2a", W, H, b)

def fig_2b():
    """목표주가가 만들어지는 길 — 가정(빨강 꼬리표)과 계산(검정)을 가른 드로잉."""
    must_be_in_md("13,000", "14.2%", "1,850", "1,400", "2,800만 주", "5,000원", "20배", "10만 원")
    W, H = 2400, 1080; b = []
    y0 = head(b, "DRAWING", "목표주가 10만 원은 가정 세 개를 거쳐 나온다")
    steps = [("매출", "13,000억", True, "13% 성장"), ("영업이익", "1,850억", True, "이익률 14.2%"),
             ("순이익", "1,400억", False, ""), ("EPS", "5,000원", False, "÷ 2,800만 주"), ("목표주가", "10만 원", True, "× PER 20배")]
    bw, gap, x = 380, 70, 80; y = y0 + 140
    for k, (t1, v, assume, tag) in enumerate(steps):
        b.append(sbox(x, y, bw, 220, SIG if assume and k == 4 else INK, SOFT if k < 4 else SIG_SOFT, 5))
        b.append(T(x + bw / 2, y + 80, t1, "body", SUB, 700, "middle"))
        b.append(T(x + bw / 2, y + 160, v, size=54, fill=INK, w=800, anchor="middle", font=MONO if v[0].isdigit() else SANS))
        if tag:
            col = SIG_T if assume else MUTE
            b.append(T(x + bw / 2, y + 300, tag, "body", col, 800 if assume else 500, "middle"))
            if assume: b.append(T(x + bw / 2, y - 30, "가정", "note", SIG_T, 800, "middle"))
        if k < len(steps) - 1: b.append(sarrow(x + bw + 8, y + 110, x + bw + gap - 8, y + 110, INK))
        x += bw + gap
    b.append(T(80, H - 60, "빨간 글자 = 애널리스트가 고른 가정. 셋 중 하나만 빗나가도 마지막 칸이 바뀐다. 가상의 예시", "note", MUTE))
    return save("2b", W, H, b)

def fig_2c():
    """같은 주가, 다른 PER — 어느 해 이익으로 나누느냐(축 0부터)."""
    must_be_in_md("79,000원", "4,000원", "19.8배", "15.8배", "20배")
    W, H = 2400, 980; b = []
    y0 = head(b, "CHART · 가상의 B사", "같은 79,000원이 19.8배도 되고 15.8배도 된다")
    gx0, gx1, mx = 620, 2200, 24.0
    X = lambda v: gx0 + (gx1 - gx0) * v / mx
    for v in (0, 5, 10, 15, 20):
        b.append(L(X(v), y0 + 20, X(v), y0 + 470, RULE, 2)); b.append(T(X(v), y0 + 520, f"{v}배", "note", MUTE, 500, "middle", font=MONO))
    for k, (lab, sub_, v) in enumerate([("2026년 예상 EPS로", "79,000 ÷ 4,000", 19.75), ("2027년 예상 EPS로", "79,000 ÷ 5,000", 15.8)]):
        y = y0 + 60 + k * 210
        b.append(T(80, y + 50, lab, "body", INK, 800)); b.append(T(80, y + 106, sub_, "note", MUTE, 500, font=MONO))
        b.append(R(gx0, y + 10, X(v) - gx0, 110, INK if k == 0 else SUB))
        b.append(T(X(v) + 20, y + 86, f"{round(v, 1)}배", size=52, fill=INK, w=800, font=MONO))
    b.append(f'<path d="M{X(20):.0f} {y0+10:.0f} V{y0+480:.0f}" stroke="{SIG}" stroke-width="6" stroke-dasharray="16 10"/>')
    b.append(T(X(20) + 16, y0 + 10, "목표 PER 20배", "body", SIG_T, 800))
    b.append(T(80, H - 50, "가상의 예시", "note", MUTE))
    return save("2c", W, H, b)

# ───────────────────────── 3장 ─────────────────────────
def chat(b, x, y, w, h, ask, lines_, title):
    b.append(R(x, y, w, h, SCR, SCR_EDGE, 4))
    b.append(R(x, y, w, 70, SCR2))
    for k in range(3): b.append(f'<circle cx="{x+40+k*34}" cy="{y+35}" r="10" fill="{SCR_EDGE}"/>')
    b.append(T(x + w - 30, y + 48, title, size=30, fill=SCR_SUB, w=700, anchor="end", font=MONO, ls=4))
    b.append(R(x + w - 40 - tw(ask, size=34) - 60, y + 110, tw(ask, size=34) + 60, 80, SIG, rx=0))
    b.append(T(x + w - 70, y + 163, ask, size=34, fill="#FFFFFF", w=700, anchor="end"))
    for k, (s, col, wt, fnt) in enumerate(lines_):
        lab, _, val = s.partition("|")
        if val:
            b.append(T(x + 40, y + 270 + k * 58, lab, size=34, fill=SCR_DIM, w=700))
            b.append(T(x + 150, y + 270 + k * 58, val, size=34, fill=col, w=wt, font=fnt))
        else:
            b.append(T(x + 40, y + 270 + k * 58, s, size=34, fill=col, w=wt, font=fnt))

def fig_3a():
    """같은 리포트, 두 가지 질문 — 요약 vs 네 칸 표(아티팩트)."""
    must_be_in_md("2027년 매출 13% 성장", "14.2%", "PER 20배", "리포트에 언급 없음")
    W, H = 2400, 1180; b = []
    y0 = head(b, "ARTIFACT · AI 대화창", "\"요약해 줘\"와 \"네 칸으로\"는 다른 답을 돌려준다")
    left = [("B사는 신규 고객사 공급 본격화로", SCR_T, 500, SANS), ("견조한 성장이 기대됩니다.", SCR_T, 500, SANS),
            ("증권사는 3분기 호실적과 2027년", SCR_T, 500, SANS), ("실적 개선 전망을 반영해 목표주가를", SCR_T, 500, SANS),
            ("10만 원으로 상향하고 투자의견", SCR_T, 500, SANS), ("매수를 유지했습니다.", SCR_T, 500, SANS),
            ("", SCR_T, 500, SANS), ("→ 알림 한 줄과 거의 같다", SIG, 700, SANS)]
    right = [("의견|매수 유지, 8만 → 10만 원", SCR_T, 600, SANS), ("근거|3분기 영업이익 410억 원", SCR_T, 600, SANS),
             ("가정|2027년 매출 13% 성장", SIG, 800, SANS), (" |영업이익률 14.2%", SIG, 800, SANS),
             (" |목표 PER 20배", SIG, 800, SANS), ("위험|리포트에 언급 없음", SCR_SUB, 600, SANS),
             ("", SCR_T, 500, SANS), ("→ 따져 볼 것이 보인다", SIG, 700, SANS)]
    chat(b, 80, y0 + 20, 1090, 760, "요약해 줘", left, "CHAT 01")
    chat(b, 1230, y0 + 20, 1090, 760, "네 칸 표로 정리해 줘", right, "CHAT 02")
    b.append(T(80, H - 50, "가상의 대화 · 설명을 위해 만든 예시", "note", MUTE))
    return save("3a", W, H, b)

def fig_3b():
    """표가 한 칸 밀리면 — 검산으로 잡는다(인포그래픽+드로잉 표시)."""
    must_be_in_md("1,850", "11,500", "16%", "13.0%")
    W, H = 2400, 1180; b = []
    y0 = head(b, "CHART · 검산", "열이 한 칸 밀리면 2026년 이익률이 16%를 넘는다")
    def table(x, y, title, rows, bad=None):
        b.append(T(x, y, title, "head", INK, 800))
        b.append(R(x, y + 30, 1040, 70, SCR))
        cx_ = lambda c: x + 30 if c == 0 else x + 420 + (c - 1) * 290
        for c, s in enumerate(["", "2025A", "2026E", "2027E"]):
            b.append(T(cx_(c), y + 78, s, size=36, fill=SCR_T, w=700, anchor="end" if c else "start", font=MONO))
        for r_, row in enumerate(rows):
            yy = y + 170 + r_ * 80
            for c, s in enumerate(row):
                hit = bad == (r_, c)
                if hit: b.append(scircle(cx_(c) - 66, yy - 14, 64))
                b.append(T(cx_(c), yy, s, size=40, fill=SIG_T if hit else INK, w=800 if hit else 600, anchor="end" if c else "start", font=MONO if c else SANS))
            b.append(L(x, yy + 26, x + 1040, yy + 26, RULE, 2))
    ok = [("매출", "10,000", "11,500", "13,000"), ("영업이익", "1,200", "1,500", "1,850"), ("이익률", "12.0%", "13.0%", "14.2%")]
    shifted = [("매출", "10,000", "11,500", "13,000"), ("영업이익", "1,500", "1,850", "—"), ("이익률(검산)", "15.0%", "16.1%", "?")]
    table(80, y0 + 40, "원문", ok)
    table(1280, y0 + 40, "한 칸 밀려 읽힌 표", shifted, bad=(1, 2))
    b.append(sbox(1280, y0 + 470, 1040, 240, SIG, SIG_SOFT, 5))
    b.append(T(1320, y0 + 545, "1,850 ÷ 11,500 = 16.1%", "body", INK, 800))
    b.append(T(1320, y0 + 605, "리포트에 적힌 13.0%와 다르다", "body", INK, 700))
    b.append(T(1320, y0 + 665, "→ 다시 계산하면 열 밀림이 드러난다", "body", SIG_T, 700))
    b.append(T(80, H - 50, "가상의 예시 · 단위 억 원", "note", MUTE))
    return save("3b", W, H, b)

def fig_3c():
    """리포트를 AI에게 넘기는 순서(드로잉)."""
    W, H = 2400, 800; b = []
    y0 = head(b, "DRAWING", "넘기고, 옮기고, 다시 계산하고, 대조한다")
    steps = [("리포트 PDF", "한 편씩"), ("원문 단위 그대로", "숫자만 표로"), ("다시 계산", "이익률·EPS|목표주가"), ("원문과 대조", "틀린 칸 고치기"), ("네 칸 표", "의견·근거|가정·위험")]
    bw, gap, x, y = 380, 70, 80, y0 + 60
    for k, (t1, t2) in enumerate(steps):
        last = k == len(steps) - 1
        b.append(sbox(x, y, bw, 260, SIG if last else INK, SIG_SOFT if last else None, 5))
        b.append(T(x + bw / 2, y + 96, t1, "body", INK, 800, "middle"))
        for j, s in enumerate(t2.split("|")): b.append(T(x + bw / 2, y + 160 + j * 52, s, "note", MUTE, 500, "middle"))
        if not last: b.append(sarrow(x + bw + 8, y + 120, x + bw + gap - 8, y + 120, INK))
        x += bw + gap
    return save("3c", W, H, b)

FIGS = [fig_p1, fig_1a, fig_1b, fig_2a, fig_2b, fig_2c, fig_3a, fig_3b, fig_3c]
if __name__ == "__main__":
    for f in FIGS: print(f())
