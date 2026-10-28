# -*- coding: utf-8 -*-
"""
2권 『질문이 바뀌면 경제가 보인다』 표지 — ‘경제뉴스 노선도’.
이 책의 핵심(뉴스가 내 돈까지 오는 ‘경로’, 단어와 단어 사이의 ‘길’)을 지하철 노선도로 그린다.
여섯 노선(질문·매크로·기업·뉴스·루틴·생활)이 서로 다른 색으로 ‘내 계좌’ 환승역에 모인다.
산출: build/img/book2_cover.png (1240×1835). 2배 크기 SVG로 그린 뒤 줄인다.
"""
import pathlib, cairosvg
from PIL import Image, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent
IMG = ROOT / "build" / "img"; IMG.mkdir(parents=True, exist_ok=True)

W, H = 2480, 3670
F = "Noto Sans CJK KR"
PAPER, INK, SUB, GOLD = "#FFFBF2", "#16213E", "#5B6478", "#F5B841"
# 노선 색(이름, 색, 노선 설명) — 표지 아래 ‘노선 안내’와 같음
LINES = {
    "q":   ("질문선",   "#E5484D", "용어 말고 연결고리"),
    "mac": ("매크로선", "#2F6FE4", "전쟁·유가·물가·금리"),
    "biz": ("기업선",   "#1FA67A", "매출 · 이익 · 현금흐름"),
    "news":("뉴스선",   "#F08A24", "출처 · 인과 · 편향 점검"),
    "rt":  ("루틴선",   "#8B5CF6", "하루 10분 · 일주일 흐름"),
    "life":("생활선",   "#14A3B8", "생활비 · 대출 · 연금"),
}

def T(x, y, s, size, fill=INK, w=700, anchor="start", ls=0):
    return (f'<text x="{x}" y="{y}" font-family="{F}" font-size="{size}" font-weight="{w}" fill="{fill}" '
            f'text-anchor="{anchor}" letter-spacing="{ls}">{s}</text>')

def text_w(t, size, weight="Bold"):
    return ImageFont.truetype(f"/usr/share/fonts/opentype/noto/NotoSansCJK-{weight}.ttc", size, index=1).getlength(t)

def line(key, pts):
    col = LINES[key][1]
    d = "M" + " L".join(f"{x} {y}" for x, y in pts)
    return f'<path d="{d}" fill="none" stroke="{col}" stroke-width="30" stroke-linecap="round" stroke-linejoin="round"/>'

def station(key, x, y, label, pos="up", terminal=False):
    """역 표시 + 이름. pos: up/down/left/right"""
    col = LINES[key][1]
    r = 34 if terminal else 24
    out = [f'<circle cx="{x}" cy="{y}" r="{r}" fill="#FFFFFF" stroke="{col if not terminal else INK}" stroke-width="{12 if terminal else 10}"/>']
    size = 48 if terminal else 44
    if pos == "up":    out.append(T(x, y-56, label, size, INK, 800 if terminal else 700, "middle"))
    if pos == "down":  out.append(T(x, y+86, label, size, INK, 800 if terminal else 700, "middle"))
    if pos == "left":  out.append(T(x-50, y+15, label, size, INK, 800 if terminal else 700, "end"))
    if pos == "right": out.append(T(x+50, y+15, label, size, INK, 800 if terminal else 700, "start"))
    return "".join(out)

def build():
    b = [f'<rect width="{W}" height="{H}" fill="{PAPER}"/>']
    # ① 시리즈 꼬리표(색 점 6개) + 부제
    b.append(f'<rect x="150" y="110" width="1010" height="86" rx="43" fill="#FFFFFF" stroke="#E7DFCE" stroke-width="4"/>')
    for i, k in enumerate(LINES):
        b.append(f'<circle cx="{205 + i*40}" cy="153" r="13" fill="{LINES[k][1]}"/>')
    b.append(T(455, 170, "호차차의 AI 읽기 · 세 번째 이야기", 46, INK, 800))
    b.append(T(150, 300, "금리·환율·실적 뉴스를 내 돈의 언어로 번역하는 직장인 AI 경제 루틴", 52, SUB, 700))
    # ② 제목 + 노선 줄무늬
    b.append(T(140, 560, "질문이 바뀌면", 225, INK, 900, ls=-6))
    b.append(T(140, 810, "경제가 보인다", 225, INK, 900, ls=-6))
    for i, k in enumerate(LINES):
        b.append(f'<rect x="{150 + i*228}" y="862" width="214" height="20" rx="10" fill="{LINES[k][1]}"/>')
    # ③ 오른쪽: 한 줄 카피 + 지은이
    for i, s in enumerate(["흩어진 경제뉴스가", "한 장의 노선도로 이어지면,", "뉴스는 내 돈의 언어가 된다"]):
        b.append(T(1640, 470 + i*80, s, 54, INK if i < 2 else "#2F6FE4", 700 if i < 2 else 800))
    b.append(T(1640, 790, "호차차", 82, INK, 900) + T(1640 + text_w("호차차", 82, "Black") + 24, 790, "지음", 56, SUB, 500))
    # ④ 말풍선(프롤로그 첫 장면) — 꼬리가 ‘전쟁’역을 가리킴
    q = "“중동에서 전쟁 났다던데, 기름값 또 오르는 거 아니야?”"
    bw = text_w(q, 52) + 110
    b.append(f'<path d="M150 965 h{bw} a36 36 0 0 1 36 36 v74 a36 36 0 0 1 -36 36 h{-(bw-250)} l-70 74 l6 -74 '
             f'h-150 a36 36 0 0 1 -36 -36 v-74 a36 36 0 0 1 36 -36 z" fill="#FFFFFF" stroke="{INK}" stroke-width="6"/>')
    b.append(T(150 + 55, 1060, q, 52, INK, 700))
    # ⑤ 노선도 판
    b.append(f'<rect x="150" y="1230" width="2180" height="1680" rx="46" fill="#FFFFFF" stroke="#E7DFCE" stroke-width="5"/>')
    # 강(장식) — 노선도 느낌
    b.append(f'<path d="M150 2520 C 700 2400, 900 2860, 1500 2760 S 2200 2540, 2330 2600" fill="none" stroke="#E4EEF9" stroke-width="90" stroke-linecap="round"/>')
    hub = (1010, 1995, 460, 170)                     # 내 계좌 환승역 (x, y, w, h)
    # 노선들
    b.append(line("mac",  [(300, 1400), (1000, 1400), (1240, 1640), (1240, 1995)]))
    b.append(line("biz",  [(2180, 1560), (1660, 1560), (1400, 1820), (1400, 1995)]))
    b.append(line("q",    [(300, 2080), (1010, 2080)]))
    b.append(line("life", [(1470, 2080), (2180, 2080)]))
    b.append(line("news", [(1100, 2165), (1100, 2400), (850, 2650), (300, 2650)]))
    b.append(line("rt",   [(1380, 2165), (1380, 2400), (1630, 2650), (2180, 2650)]))
    # 역
    st = [
        ("mac", 300, 1400, "전쟁", "up", True), ("mac", 530, 1400, "유가", "up"), ("mac", 760, 1400, "물가", "up"),
        ("mac", 1000, 1400, "금리", "up"), ("mac", 1120, 1520, "환율", "left"), ("mac", 1240, 1800, "중앙은행", "left"),
        ("biz", 2180, 1560, "매출", "up", True), ("biz", 1930, 1560, "영업이익", "up"), ("biz", 1680, 1560, "현금흐름", "up"),
        ("biz", 1530, 1690, "재무제표", "right"), ("biz", 1400, 1900, "기대·심리", "right"),
        ("q", 300, 2080, "경제뉴스", "up", True),
        ("life", 1720, 2080, "생활비", "up"), ("life", 1950, 2080, "대출", "up"), ("life", 2180, 2080, "연금·ETF", "up", True),
        ("news", 1100, 2310, "팩트체크", "left"), ("news", 975, 2525, "확증편향", "left"), ("news", 760, 2650, "침묵 읽기", "down"),
        ("news", 530, 2650, "인과 사슬", "down"), ("news", 300, 2650, "1차 소스", "down", True),
        ("rt", 1380, 2310, "하루 10분", "right"), ("rt", 1630, 2650, "일주일 흐름", "down"), ("rt", 1905, 2650, "복기 노트", "down"),
        ("rt", 2180, 2650, "AI 경제 선생", "down", True),
    ]
    for s in st:
        b.append(station(*s[:5], terminal=(len(s) > 5 and s[5])))
    # ‘질문’ 역: 물음표 → 느낌표(질문이 바뀌면 보인다)
    qx, qy = 680, 2080
    b.append(f'<circle cx="{qx}" cy="{qy}" r="58" fill="{LINES["q"][1]}" stroke="#FFFFFF" stroke-width="10"/>')
    b.append(T(qx, qy+30, "?", 84, "#FFFFFF", 900, "middle"))
    b.append(T(qx, qy-86, "질문 바꾸기", 48, LINES["q"][1], 900, "middle"))
    # 내 계좌 환승역
    x, y, w, h = hub
    b.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="85" fill="{INK}" stroke="#FFFFFF" stroke-width="12"/>')
    b.append(f'<circle cx="{x+92}" cy="{y+h/2}" r="44" fill="{GOLD}"/>' + T(x+92, y+h/2+22, "₩", 60, INK, 900, "middle"))
    b.append(T(x+292, y+h/2+26, "내 계좌", 72, "#FFFFFF", 900, "middle"))
    # ⑥ 금색 원형 배지
    cx, cy = 2150, 1200
    b.append(f'<circle cx="{cx+8}" cy="{cy+12}" r="170" fill="#000" opacity=".10"/>')
    b.append(f'<circle cx="{cx}" cy="{cy}" r="170" fill="{GOLD}" stroke="#E2A23A" stroke-width="8"/>')
    b.append(T(cx, cy-40, "AI 프롬프트", 52, INK, 900, "middle"))
    b.append(T(cx, cy+40, "33개", 76, INK, 900, "middle"))
    b.append(T(cx, cy+108, "수록!", 50, INK, 800, "middle"))
    # ⑦ 아래 띠: 노선 안내 + 프롤로그 인용
    by = 2990
    b.append(f'<rect x="0" y="{by}" width="{W}" height="{H-by}" fill="{INK}"/>')
    b.append(T(150, by+110, "노선 안내", 44, "#AEB8CC", 800, ls=6))
    for i, k in enumerate(LINES):
        name, col, desc = LINES[k]
        cx0 = 150 + (i % 2) * 640; cy0 = by + 205 + (i // 2) * 112
        b.append(f'<rect x="{cx0}" y="{cy0-34}" width="60" height="36" rx="18" fill="{col}"/>')
        b.append(T(cx0+84, cy0, name, 44, "#FFFFFF", 800) + T(cx0+84+text_w(name, 44)+20, cy0, desc, 38, "#C9D2E3", 500))
    qx0 = 1500
    b.append(T(qx0, by+170, "“", 130, GOLD, 900))
    for i, (s, col) in enumerate([("이 책은 경제를 쉽게 설명하는", "#FFFFFF"), ("책이 아닙니다.", "#FFFFFF"),
                                  ("경제를 내 일과 연결해", GOLD), ("생각하게 만드는 책입니다.", GOLD)]):
        b.append(T(qx0+60, by+180 + i*74, s, 52, col, 700))
    b.append(T(qx0+60, by+500, "– 프롤로그 중에서", 38, "#AEB8CC", 400))
    b.append(f'<path d="M150 {by+560} H2330" stroke="#FFFFFF" stroke-width="2" opacity=".18"/>')
    b.append(T(W/2, by+640, "AI에게 답 말고 경로를 물으면, 경제뉴스가 내 돈의 언어로 번역됩니다", 46, "#E6ECF5", 700, "middle"))
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{"".join(b)}</svg>'
    big = IMG / "book2_cover_2x.png"
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(big), output_width=W, output_height=H)
    out = IMG / "book2_cover.png"
    Image.open(big).convert("RGB").resize((1240, 1835), Image.LANCZOS).save(out)
    return out

if __name__ == "__main__":
    print(build())
