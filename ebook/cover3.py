# -*- coding: utf-8 -*-
"""
3권 표지 — 2권 『질문이 바뀌면 경제가 보인다』 표지와 같은 구성·색감(크림 배경, 남색·파랑 제목, 말풍선,
금색 원형 배지, 아래 파란 띠 + 아이콘 카드 + 월계관 배지)에, 저자 표지의 ‘매매법 카드 격자’ 그림을 살려 넣는다.
산출: build/img/book3_cover.png (1240×1835). 2배 크기 SVG로 그린 뒤 줄인다.
"""
import base64, io, pathlib, cairosvg
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent
IMG = ROOT / "build" / "img"; IMG.mkdir(parents=True, exist_ok=True)
GRID = ROOT / "assets" / "book3_grid.png"          # 저자 표지에서 잘라 낸 카드 격자(배경 #0D1B2E)

W, H = 2480, 3670                                    # 1240×1835의 2배
F = "Noto Sans CJK KR"
CREAM, NAVY, BLUE, GOLDTXT = "#FBF6E8", "#062447", "#0A55A0", "#A8640F"
BAND, BAND2, BADGE, GOLD = "#0B4A8A", "#0A3F78", "#F8D07A", "#F2B544"
GRIDBG = "#0D1B2E"

def T(x, y, s, size, fill=NAVY, w=400, anchor="start", ls=0):
    return (f'<text x="{x}" y="{y}" font-family="{F}" font-size="{size}" font-weight="{w}" fill="{fill}" '
            f'text-anchor="{anchor}" letter-spacing="{ls}">{s}</text>')

def text_w(t, size, weight="Bold"):
    from PIL import ImageFont
    return ImageFont.truetype(f"/usr/share/fonts/opentype/noto/NotoSansCJK-{weight}.ttc", size, index=1).getlength(t)

def laurel(cx, cy, side, h=190, col=GOLD):
    """간단한 월계수 가지(왼쪽 side=-1, 오른쪽 side=1). 줄기 + 잎 7쌍."""
    import math
    out = [f'<path d="M{cx} {cy+h/2} Q{cx-side*70} {cy} {cx} {cy-h/2}" fill="none" stroke="{col}" stroke-width="7" stroke-linecap="round"/>']
    for i in range(6):
        t = i / 5
        # 2차 베지어 위의 점
        x = (1-t)**2*cx + 2*(1-t)*t*(cx-side*70) + t**2*cx
        y = (1-t)**2*(cy+h/2) + 2*(1-t)*t*cy + t**2*(cy-h/2)
        ang = -90 + side*(35 - 10*t)
        for d in (-1, 1):
            a = ang + d*38*side
            rx, ry = 24 - 7*t, 8.5 - 2.5*t
            ox, oy = x + math.cos(math.radians(a))*rx*0.9, y + math.sin(math.radians(a))*rx*0.9
            out.append(f'<ellipse cx="{ox:.1f}" cy="{oy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{col}" '
                       f'transform="rotate({a:.1f} {ox:.1f} {oy:.1f})"/>')
    return "".join(out)

def icon(kind, cx, cy, c=NAVY):
    s = f'stroke="{c}" stroke-width="9" fill="none" stroke-linecap="round" stroke-linejoin="round"'
    if kind == "bars":      # 거래량·돌파
        return (f'<path d="M{cx-60} {cy+45} V{cy+10} M{cx-20} {cy+45} V{cy-20} M{cx+20} {cy+45} V{cy-5} '
                f'M{cx+60} {cy+45} V{cy-45}" {s}/><path d="M{cx-70} {cy+55} H{cx+75}" {s}/>'
                f'<path d="M{cx+35} {cy-62} l25 -15 l3 30" {s}/>')
    if kind == "dip":       # 손절 5% — 빠졌다 돌아오는 흔들림
        return (f'<path d="M{cx-75} {cy-25} L{cx-35} {cy-5} L{cx-5} {cy+45} L{cx+30} {cy+5} L{cx+75} {cy-40}" {s}/>'
                f'<path d="M{cx-80} {cy+5} H{cx+80}" stroke="{c}" stroke-width="5" stroke-dasharray="10 10"/>')
    if kind == "target":    # 파는 규칙 — 목표 도달
        return (f'<circle cx="{cx+35}" cy="{cy-25}" r="34" {s}/><circle cx="{cx+35}" cy="{cy-25}" r="10" fill="{c}"/>'
                f'<path d="M{cx-75} {cy+50} L{cx-35} {cy+20} L{cx-5} {cy+35} L{cx+20} {cy}" {s}/>')
    if kind == "rebound":   # 살아남은 규칙 — 급락 뒤 반등
        return (f'<path d="M{cx-75} {cy-45} L{cx-40} {cy-25} L{cx-15} {cy+45} L{cx+20} {cy+5} L{cx+70} {cy-35}" {s}/>'
                f'<circle cx="{cx-15}" cy="{cy+45}" r="14" fill="{c}"/><path d="M{cx+48} {cy-42} l24 4 l-6 22" {s}/>')
    if kind == "magnify":   # AI와 함께 의심
        return (f'<circle cx="{cx-15}" cy="{cy-10}" r="45" {s}/><path d="M{cx+18} {cy+25} L{cx+60} {cy+65}" {s}/>'
                + T(cx-15, cy+4, "AI", 40, c, 900, "middle"))
    return ""

def grid_data_uri(target_w, target_h):
    im = Image.open(GRID).convert("RGB")
    im = im.crop((0, 299, im.width, im.height))            # 맨 윗줄 제외 → 강조된 4장이 모두 온전히 보이게
    s = max(target_w / im.width, target_h / im.height)     # 패널을 꽉 채우도록(가장자리 카드는 살짝 잘림)
    im = im.resize((round(im.width*s), round(im.height*s)), Image.LANCZOS)
    l = (im.width - target_w)//2; t = (im.height - target_h)//2
    im = im.crop((l, t, l+target_w, t+target_h))
    buf = io.BytesIO(); im.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

def build():
    b = [f'<rect width="{W}" height="{H}" fill="{CREAM}"/>']
    # 배경의 은은한 상승 차트 선(2권 표지의 배경 장식에 해당)
    b.append(f'<path d="M1500 1010 L1650 960 L1760 990 L1900 880 L2030 905 L2180 780 L2330 720" fill="none" '
             f'stroke="#E9DFC6" stroke-width="10" stroke-linejoin="round"/>')
    # ① 맨 위 한 줄(부제) — 금갈색, 양옆 선
    b.append(f'<path d="M150 180 H300 M2180 180 H2330" stroke="{GOLDTXT}" stroke-width="5"/>')
    b.append(T(W/2, 200, "AI와 함께 21년 치 데이터로 돌려봤더니, 살아남은 건 몇 개뿐이었다", 62, GOLDTXT, 700, "middle"))
    # ② 제목 — 남색 2줄 + 파랑 1줄
    b.append(T(140, 520, "나는 유튜브", 220, NAVY, 900, ls=-6))
    b.append(T(140, 760, "매매법을", 220, NAVY, 900, ls=-6))
    b.append(T(140, 1000, "믿지 않았다", 220, BLUE, 900, ls=-6))
    # ③ 오른쪽 소개 + 지은이
    for i, line in enumerate(["유튜브에서 유행하는 매매법,", "정말 통했을까?", "AI와 함께 21년 치 데이터로", "하나씩 검증한 실전 기록"]):
        b.append(T(1600, 410 + i*82, line, 56, NAVY, 500))
    b.append(T(1600, 800, "호차차", 78, NAVY, 800) + T(1860, 800, "지음", 56, NAVY, 500))
    # ④ 말풍선(독자의 질문)
    b.append(f'<path d="M150 1045 h980 a40 40 0 0 1 40 40 v120 a40 40 0 0 1 -40 40 h-760 l-70 62 l10 -62 h-160 '
             f'a40 40 0 0 1 -40 -40 v-120 a40 40 0 0 1 40 -40 z" fill="#FFFFFF" stroke="{NAVY}" stroke-width="7"/>')
    b.append(T(660, 1130, "“승률 80% 매매법이라던데,", 58, NAVY, 700, "middle"))
    b.append(T(660, 1205, "진짜 통할까?”", 58, NAVY, 700, "middle"))
    # ⑤ 가운데 그림: 매매법 카드 격자(저자 표지 그림) — 둥근 패널
    px, py, pw, ph = 150, 1300, 2180, 1364                # 격자 그림 비율(1.598) 그대로
    b.append(f'<rect x="{px+14}" y="{py+22}" width="{pw}" height="{ph}" rx="46" fill="#0B1A2E" opacity=".18"/>')
    b.append(f'<clipPath id="pc"><rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="46"/></clipPath>')
    b.append(f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="46" fill="{GRIDBG}"/>')
    b.append(f'<image x="{px}" y="{py}" width="{pw}" height="{ph}" clip-path="url(#pc)" href="{grid_data_uri(pw, ph)}"/>')
    # 패널 위 라벨
    # ⑥ 금색 원형 배지(2권의 ‘AI 프롬프트 20선 수록!’ 자리)
    cx, cy = 2120, 1215
    b.append(f'<circle cx="{cx+8}" cy="{cy+12}" r="185" fill="#000" opacity=".12"/>')
    b.append(f'<circle cx="{cx}" cy="{cy}" r="185" fill="{BADGE}" stroke="#E2A93C" stroke-width="8"/>')
    b.append(T(cx, cy-35, "실전 규칙", 64, NAVY, 900, "middle"))
    b.append(T(cx, cy+45, "카드 4종", 64, NAVY, 900, "middle"))
    b.append(T(cx, cy+118, "수록!", 56, NAVY, 800, "middle"))
    # ⑦ 아래 파란 띠
    by = 2730
    b.append(f'<rect x="0" y="{by}" width="{W}" height="{H-by}" fill="{BAND}"/>')
    b.append(T(150, by+150, "유튜브 매매법을 믿지 말고,", 92, "#FFFFFF", 800) +
             T(150+1059, by+150, "숫자로 확인하라!", 92, GOLD, 900))     # 앞 문구 실측 폭 1059
    cards = [("bars", "거래량·돌파", "착각 검증"), ("dip", "손절 5%의", "진실"), ("target", "파는 규칙의", "힘"),
             ("rebound", "살아남은", "규칙 공개"), ("magnify", "AI와 함께", "의심하는 법")]
    for i, (k, l1, l2) in enumerate(cards):
        x = 150 + i*300; y = by+230
        b.append(f'<rect x="{x}" y="{y}" width="270" height="330" rx="34" fill="{CREAM}"/>')
        b.append(icon(k, x+135, y+105))
        b.append(T(x+135, y+235, l1, 40, NAVY, 800, "middle") + T(x+135, y+288, l2, 40, NAVY, 800, "middle"))
    # 인용(프롤로그)
    qx = 1720
    b.append(T(qx, by+300, "“", 140, GOLD, 900))
    for i, (line, col) in enumerate([("이 책에 나오는 숫자는", "#FFFFFF"), ("정답이 아니라,", "#FFFFFF"),
                                     ("의심을 끝까지", GOLD), ("밀어붙인 기록입니다.", GOLD)]):
        b.append(T(qx+70, by+300 + i*72, line, 54, col, 700))
    b.append(T(qx+70, by+600, "– 프롤로그 중에서", 40, "#C9D7E8", 400))
    # ⑧ 월계관 배지 3개
    badges = [("「나는 AI에게 종목을 묻지 않았다」", "두 번째 이야기", "#FFFFFF"),
              ("상장폐지 983개 포함", "21년 치 데이터로 검증", "#FFFFFF"),
              ("유명한 매매법을", "숫자로 하나씩 해부", GOLD)]
    for i, (l1, l2, col) in enumerate(badges):
        cxb = (470, 1250, 2010)[i]; cyb = by+770
        fs = 35 if i == 0 else 44                              # 첫 배지는 글이 길어 조금 작게
        half = max(text_w(l1, fs), text_w(l2, fs)) / 2
        b.append(laurel(cxb-half-62, cyb, -1) + laurel(cxb+half+62, cyb, 1))   # 글자 폭에 붙여서
        b.append(T(cxb, cyb-10, l1, fs, col, 800, "middle"))
        b.append(T(cxb, cyb+52, l2, fs, col, 800, "middle"))
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{"".join(b)}</svg>'
    big = IMG / "book3_cover_2x.png"
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(big), output_width=W, output_height=H)
    out = IMG / "book3_cover.png"
    Image.open(big).convert("RGB").resize((1240, 1835), Image.LANCZOS).save(out)
    return out

if __name__ == "__main__":
    print(build())
