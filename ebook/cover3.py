# -*- coding: utf-8 -*-
"""
3권 표지 — 2권 『질문이 바뀌면 경제가 보인다』와 같은 구성·색감(크림 배경, 남색·파랑 제목, 말풍선, 금색 원형 배지,
아래 파란 띠 + 아이콘 카드)으로 그린다. 가운데 그림은 저자 표지의 ‘유튜브 매매법 썸네일 격자’(30장, X 표시,
살아남은 4장 강조)를 같은 배치·문구로 2권 팔레트에 맞춰 벡터로 다시 그린 것.
산출: build/img/book3_cover.png (1240×1835). 2배 크기 SVG로 그린 뒤 줄인다.
"""
import hashlib, pathlib, cairosvg
from PIL import Image, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent
IMG = ROOT / "build" / "img"; IMG.mkdir(parents=True, exist_ok=True)

W, H = 2480, 3670                                    # 1240×1835의 2배
F = "Noto Sans CJK KR"
CREAM, NAVY, BLUE, GOLDTXT = "#FBF6E8", "#062447", "#0A55A0", "#A8640F"
BAND, BADGE, GOLD = "#0B4A8A", "#F8D07A", "#F2B544"

# 저자 표지의 격자 그대로: (문구, 영상 길이) / 영상 길이가 None이면 살아남은 카드
ROWS = [
    [("승률 90% 매매법", "23:40"), ("무조건 오르는 패턴", "11:28"), ("이것만 알면 끝", "9:14"), ("급등주 공식", "5:26"), ("거래량 폭발 종목", "20:31")],
    [("돌파 매매 비법", "11:33"), ("급락 반등", None), ("정배열 필승법", "15:21"), ("손절 5% 원칙", "10:25"), ("세력 매집 신호", "18:14")],
    [("외국인 따라잡기", "23:46"), ("골든크로스 매수", "23:15"), ("볼린저 돌파", "22:37"), ("정배열 눌림목", None), ("하루 10% 단타", "16:57")],
    [("상한가 따라잡기", "4:52"), ("주도주 추격", "17:32"), ("신고가 매매", "3:51"), ("5분봉 스캘핑", "18:26"), ("이평선 돌파", "7:49")],
    [("지수 과매도", None), ("장대양봉 매수", "13:49"), ("눌림 없는 급등", "23:24"), ("차트 하나로 끝", "19:19"), ("100% 수익 공식", "6:35")],
    [("RSI 70 매도", "12:37"), ("시초가 매매", "4:59"), ("파는 규칙", None), ("테마주 순환매", "24:43"), ("급등 직전 신호", "5:20")],
]

def T(x, y, s, size, fill=NAVY, w=400, anchor="start", ls=0):
    return (f'<text x="{x}" y="{y}" font-family="{F}" font-size="{size}" font-weight="{w}" fill="{fill}" '
            f'text-anchor="{anchor}" letter-spacing="{ls}">{s}</text>')

def text_w(t, size, weight="Bold"):
    return ImageFont.truetype(f"/usr/share/fonts/opentype/noto/NotoSansCJK-{weight}.ttc", size, index=1).getlength(t)

def series(label, n, up):
    """카드 안 작은 차트 선: 문구마다 고정된 모양(재현 가능). up=True면 꾸준히 오르는 선."""
    h = hashlib.md5(label.encode()).digest()
    ys = []
    for i in range(n):
        noise = (h[i % 16] / 255 - .5) * (.10 if up else .22)
        base = (.85 - .7 * i / (n-1)) if up else (.30 + .45 * i / (n-1))
        ys.append(min(.95, max(.05, base + noise)))
    return ys

def tile(x, y, w, h, label, time):
    tx, ty, tw, th = x+14, y+14, w-28, h-86          # 썸네일 영역
    if time is None:                                  # 살아남은 카드(강조)
        pts = " ".join(f"{tx+24+(tw-48)*i/9:.0f},{ty+18+(th-36)*v:.0f}" for i, v in enumerate(series(label, 10, True)))
        return (f'<rect x="{x-12}" y="{y-12}" width="{w+24}" height="{h+24}" rx="34" fill="{BLUE}" opacity=".16"/>'
                f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="24" fill="#FFFFFF" stroke="{BLUE}" stroke-width="7"/>'
                f'<rect x="{tx}" y="{ty}" width="{tw}" height="{th}" rx="14" fill="{NAVY}"/>'
                f'<polyline points="{pts}" fill="none" stroke="{GOLD}" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>'
                f'<circle cx="{tx+tw-34}" cy="{ty+34}" r="25" fill="{GOLD}"/>'
                f'<path d="M{tx+tw-46} {ty+34} l9 10 l17 -19" fill="none" stroke="{NAVY}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>'
                + T(x+w/2, y+h-24, label, 40, BLUE, 900, "middle"))
    pts = " ".join(f"{tx+18+(tw-36)*i/9:.0f},{ty+16+(th-32)*v:.0f}" for i, v in enumerate(series(label, 10, False)))
    pcx, pcy = tx+tw/2, ty+th/2
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="24" fill="#F1F4F8" stroke="#D3DCE6" stroke-width="3"/>'
            f'<rect x="{tx}" y="{ty}" width="{tw}" height="{th}" rx="14" fill="#E3E9F0"/>'
            f'<polyline points="{pts}" fill="none" stroke="#B3BFCD" stroke-width="6" stroke-linejoin="round"/>'
            f'<path d="M{pcx-16} {pcy-22} L{pcx+24} {pcy} L{pcx-16} {pcy+22} Z" fill="#C3CDD8"/>'
            f'<rect x="{tx+tw-92}" y="{ty+10}" width="82" height="36" rx="8" fill="#D2DAE3"/>'
            + T(tx+tw-51, ty+37, time, 25, "#7F8C9D", 700, "middle")
            + f'<path d="M{x+18} {y+h-18} L{x+w-18} {y+18}" stroke="#AFBAC8" stroke-width="4" stroke-linecap="round"/>'
            + T(x+22, y+h-26, label, 33, "#8E99A8", 700))

def grid(px, py, pw, ph):
    """저자 표지와 같은 6줄×5칸, 짝수 줄은 반 칸쯤 밀린 배치."""
    out = [f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="46" fill="#E9EFF6"/>',
           f'<clipPath id="gc"><rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="46"/></clipPath><g clip-path="url(#gc)">']
    cols, gap, off = 5, 30, 64                        # off: 짝수 줄을 살짝 밀어 벽돌처럼(저자 그림과 같은 리듬)
    tw = (pw - 2*40 - (cols-1)*gap - off) / cols      # 30장이 모두 패널 안에 온전히
    th = (ph - 2*36 - 5*gap) / 6
    hi = []
    for r, row in enumerate(ROWS):
        shift = 40 if r % 2 == 0 else 40 + off
        for c, (label, time) in enumerate(row):
            x = px + shift + c*(tw+gap); y = py + 36 + r*(th+gap)
            (hi if time is None else out).append(tile(x, y, tw, th, label, time))
    out += hi                                           # 강조 카드는 맨 위에
    out.append('</g>')
    return "".join(out)

def icon(kind, cx, cy, c=NAVY):
    s = f'stroke="{c}" stroke-width="9" fill="none" stroke-linecap="round" stroke-linejoin="round"'
    if kind == "bars":
        return (f'<path d="M{cx-60} {cy+45} V{cy+10} M{cx-20} {cy+45} V{cy-20} M{cx+20} {cy+45} V{cy-5} '
                f'M{cx+60} {cy+45} V{cy-45}" {s}/><path d="M{cx-70} {cy+55} H{cx+75}" {s}/>'
                f'<path d="M{cx+35} {cy-62} l25 -15 l3 30" {s}/>')
    if kind == "dip":
        return (f'<path d="M{cx-75} {cy-25} L{cx-35} {cy-5} L{cx-5} {cy+45} L{cx+30} {cy+5} L{cx+75} {cy-40}" {s}/>'
                f'<path d="M{cx-80} {cy+5} H{cx+80}" stroke="{c}" stroke-width="5" stroke-dasharray="10 10"/>')
    if kind == "target":
        return (f'<circle cx="{cx+35}" cy="{cy-25}" r="34" {s}/><circle cx="{cx+35}" cy="{cy-25}" r="10" fill="{c}"/>'
                f'<path d="M{cx-75} {cy+50} L{cx-35} {cy+20} L{cx-5} {cy+35} L{cx+20} {cy}" {s}/>')
    if kind == "rebound":
        return (f'<path d="M{cx-75} {cy-45} L{cx-40} {cy-25} L{cx-15} {cy+45} L{cx+20} {cy+5} L{cx+70} {cy-35}" {s}/>'
                f'<circle cx="{cx-15}" cy="{cy+45}" r="14" fill="{c}"/><path d="M{cx+48} {cy-42} l24 4 l-6 22" {s}/>')
    if kind == "magnify":
        return (f'<circle cx="{cx-15}" cy="{cy-10}" r="45" {s}/><path d="M{cx+18} {cy+25} L{cx+60} {cy+65}" {s}/>'
                + T(cx-15, cy+4, "AI", 40, c, 900, "middle"))
    return ""

def build():
    b = [f'<rect width="{W}" height="{H}" fill="{CREAM}"/>']
    # ① 맨 위 한 줄(부제)
    b.append(f'<path d="M150 180 H300 M2180 180 H2330" stroke="{GOLDTXT}" stroke-width="5"/>')
    b.append(T(W/2, 200, "AI와 함께 21년 치 데이터로 돌려봤더니, 살아남은 건 몇 개뿐이었다", 62, GOLDTXT, 700, "middle"))
    # ② 제목
    b.append(T(140, 520, "나는 유튜브", 220, NAVY, 900, ls=-6))
    b.append(T(140, 760, "매매법을", 220, NAVY, 900, ls=-6))
    b.append(T(140, 1000, "믿지 않았다", 220, BLUE, 900, ls=-6))
    # ③ 오른쪽: 소개 · 지은이 · 시리즈
    for i, line in enumerate(["유튜브에서 유행하는 매매법,", "정말 통했을까?", "AI와 함께 21년 치 데이터로", "하나씩 검증한 실전 기록"]):
        b.append(T(1600, 410 + i*82, line, 56, NAVY, 500))
    b.append(T(1600, 790, "호차차", 78, NAVY, 800) + T(1860, 790, "지음", 56, NAVY, 500))
    b.append(f'<path d="M1600 845 H2330" stroke="{GOLDTXT}" stroke-width="3" opacity=".6"/>')
    b.append(T(1600, 905, "「나는 AI에게 종목을 묻지 않았다」", 44, GOLDTXT, 700))
    b.append(T(1600, 962, "두 번째 이야기", 44, GOLDTXT, 700))
    # ④ 말풍선
    b.append(f'<path d="M150 1045 h980 a40 40 0 0 1 40 40 v120 a40 40 0 0 1 -40 40 h-760 l-70 62 l10 -62 h-160 '
             f'a40 40 0 0 1 -40 -40 v-120 a40 40 0 0 1 40 -40 z" fill="#FFFFFF" stroke="{NAVY}" stroke-width="7"/>')
    b.append(T(660, 1130, "“승률 80% 매매법이라던데,", 58, NAVY, 700, "middle"))
    b.append(T(660, 1205, "진짜 통할까?”", 58, NAVY, 700, "middle"))
    # ⑤ 가운데 그림: 유튜브 매매법 썸네일 격자(살아남은 4장 강조)
    b.append(grid(150, 1300, 2180, 1560))
    # ⑥ 금색 원형 배지
    cx, cy = 2120, 1215
    b.append(f'<circle cx="{cx+8}" cy="{cy+12}" r="185" fill="#000" opacity=".10"/>')
    b.append(f'<circle cx="{cx}" cy="{cy}" r="185" fill="{BADGE}" stroke="#E2A93C" stroke-width="8"/>')
    b.append(T(cx, cy-35, "실전 규칙", 64, NAVY, 900, "middle"))
    b.append(T(cx, cy+45, "카드 4종", 64, NAVY, 900, "middle"))
    b.append(T(cx, cy+118, "수록!", 56, NAVY, 800, "middle"))
    # ⑦ 아래 파란 띠: 한 줄 메시지 · 아이콘 카드 · 인용 · 데이터 한 줄
    by = 2940
    b.append(f'<rect x="0" y="{by}" width="{W}" height="{H-by}" fill="{BAND}"/>')
    head = "유튜브 매매법을 믿지 말고, "
    b.append(T(150, by+140, head, 88, "#FFFFFF", 800) + T(150+text_w(head, 88), by+140, "숫자로 확인하라!", 88, GOLD, 900))
    cards = [("bars", "거래량·돌파", "착각 검증"), ("dip", "손절 5%의", "진실"), ("target", "파는 규칙의", "힘"),
             ("rebound", "살아남은", "규칙 공개"), ("magnify", "AI와 함께", "의심하는 법")]
    for i, (k, l1, l2) in enumerate(cards):
        x = 150 + i*300; y = by+205
        b.append(f'<rect x="{x}" y="{y}" width="270" height="320" rx="34" fill="{CREAM}"/>')
        b.append(icon(k, x+135, y+100))
        b.append(T(x+135, y+228, l1, 40, NAVY, 800, "middle") + T(x+135, y+280, l2, 40, NAVY, 800, "middle"))
    qx = 1720
    b.append(T(qx, by+300, "“", 140, GOLD, 900))
    for i, (line, col) in enumerate([("이 책에 나오는 숫자는", "#FFFFFF"), ("정답이 아니라,", "#FFFFFF"),
                                     ("의심을 끝까지", GOLD), ("밀어붙인 기록입니다.", GOLD)]):
        b.append(T(qx+70, by+290 + i*70, line, 54, col, 700))
    b.append(T(qx+70, by+575, "– 프롤로그 중에서", 40, "#C9D7E8", 400))
    b.append(f'<path d="M150 {by+615} H2330" stroke="#FFFFFF" stroke-width="2" opacity=".25"/>')
    b.append(T(W/2, by+690, "2006~2026 · 21년 치 한국 시장 데이터 · 상장폐지 983개 종목 포함 · 신호 조합 1,854개 검증",
               42, "#D6E2F0", 500, "middle"))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
           f'{"".join(b)}</svg>')
    big = IMG / "book3_cover_2x.png"
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(big), output_width=W, output_height=H)
    out = IMG / "book3_cover.png"
    Image.open(big).convert("RGB").resize((1240, 1835), Image.LANCZOS).save(out)
    return out

if __name__ == "__main__":
    print(build())
