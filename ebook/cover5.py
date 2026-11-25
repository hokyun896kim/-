# -*- coding: utf-8 -*-
"""
5권 『매수 의견만 있는 나라』 표지.
방향: 미래형 = 네온·글로우가 아니라 '트레이딩 터미널'의 정밀함 — 검푸른 화면, 고정폭 숫자, 신호색 빨강 한 가지.
      ①~④권(2권 크림·선 그림, 3권 먹색+금색 모눈, 4권 흰 종이+형광 노랑)과 겹치지 않게.
그림: 전부 BUY로 채워진 상태판(리서치 목록). 그 가운데 한 칸만 열려
      '목표주가 100,000 = EPS 5,000 × PER 20.0x'가 보이고 20.0x에만 빨간 밑줄 — "이 목표주가는 무엇을 가정했나".
필수 글자: 제목·저자명·출판사명(유페이퍼)·시리즈. 산출: build/img/book5_cover.png (1240×1835), _2x
"""
import pathlib, random, cairosvg
from PIL import Image, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent
IMG = ROOT / "build" / "img"; IMG.mkdir(parents=True, exist_ok=True)
W, H = 2480, 3670
SANS, MONO = "Noto Sans CJK KR", "JetBrains Mono"
BG, PANEL, CELL, EDGE = "#0D1117", "#11161D", "#141A22", "#252D38"
TXT, SUB, DIM, FAINT, SIG = "#EEF1F5", "#A9B2BD", "#5E6875", "#38414D", "#FF4B3E"
BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"

def T(x, y, s, size, fill=TXT, w=700, anchor="start", font=SANS, ls=0):
    return (f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" font-weight="{w}" fill="{fill}" '
            f'text-anchor="{anchor}" letter-spacing="{ls}">{s}</text>')

def tw(s, size):
    return ImageFont.truetype(BOLD, size, index=1).getlength(s)

def build():
    rnd = random.Random(5)
    b = [f'<rect width="{W}" height="{H}" fill="{BG}"/>']
    # 머리글(고정폭) + 시리즈
    b.append(T(150, 200, "RESEARCH / TARGET PRICE / AI", 40, SUB, 500, font=MONO, ls=6))
    b.append(T(2330, 200, "호차차의 AI 읽기 ⑤", 42, SUB, 700, "end"))
    b.append(f'<path d="M150 250 H2330" stroke="{EDGE}" stroke-width="4"/>')
    # 화면 모서리 표식(좌표 눈금) — 터미널 화면이라는 신호, 장식은 여기까지
    for x, y, dx, dy in [(150, 300, 1, 1), (2330, 300, -1, 1)]:
        b.append(f'<path d="M{x} {y+60} V{y} H{x+60*dx}" fill="none" stroke="{DIM}" stroke-width="4"/>')

    # 제목: 굵은 고딕, '매수'만 신호색
    b.append(T(140, 700, f'<tspan fill="{SIG}">매수</tspan> 의견만', 290, TXT, 900, ls=-8))
    b.append(T(140, 1010, "있는 나라", 290, TXT, 900, ls=-8))
    b.append(T(150, 1170, "AI와 함께 읽는 증권사 리포트,", 62, SUB, 500))
    b.append(T(150, 1262, "목표주가 뒤에 숨은 가정들", 62, SUB, 500))

    # 상태판: 10열 × 8행, 전부 BUY
    x0, y0, cols, rows, cw, ch, g = 150, 1440, 10, 8, 202, 150, 16
    hot = (5, 6)                      # (행, 열) 열린 칸
    b.append(T(x0, y0 - 34, "COVERAGE  ·  OPINION", 30, DIM, 500, font=MONO, ls=4))
    b.append(T(x0 + cols * (cw + g) - g, y0 - 34, "UPDATED 07:58", 30, DIM, 500, "end", font=MONO, ls=4))
    for r in range(rows):
        for c in range(cols):
            x, y = x0 + c * (cw + g), y0 + r * (ch + g)
            on = (r, c) == hot
            b.append(f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" fill="{CELL}" '
                     f'stroke="{SIG if on else EDGE}" stroke-width="{8 if on else 3}"/>')
            b.append(T(x + 18, y + 40, f"R-{rnd.randint(100, 999)}", 24, FAINT, 500, font=MONO, ls=2))
            b.append(T(x + cw / 2, y + 108, "BUY", 50, TXT if on else DIM, 700, "middle", font=MONO, ls=4))
    # 열린 칸 → 아래 패널로 곧은 연결선(사선 금지)
    hx = x0 + hot[1] * (cw + g) + cw / 2
    hy = y0 + hot[0] * (ch + g) + ch
    px = x0 + 4 * (cw + g); py = y0 + 6 * (ch + g); pw, ph = 2330 - px, 560   # 열린 칸 바로 아래에 붙인 상세 창
    b.append(f'<path d="M{hx} {hy} V{py}" stroke="{SIG}" stroke-width="5"/>')
    # 패널(화면 위에 뜬 상세 창): 단색 면 + 빨간 윗줄, 그림자·글로우 없음
    b.append(f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" fill="{PANEL}" stroke="{EDGE}" stroke-width="4"/>')
    b.append(f'<rect x="{px}" y="{py}" width="{pw}" height="14" fill="{SIG}"/>')
    b.append(T(px + 70, py + 110, "TARGET PRICE", 36, DIM, 500, font=MONO, ls=6))
    b.append(T(px + 70, py + 250, "100,000", 130, TXT, 700, font=MONO, ls=2))
    b.append(T(px + 70, py + 360, "= EPS 5,000 × PER", 56, SUB, 500, font=MONO))
    ex = px + 70 + ImageFont.truetype("/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Medium.ttf", 56).getlength("= EPS 5,000 × PER ") \
        if pathlib.Path("/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Medium.ttf").exists() else px + 70 + 56 * 0.6 * 18
    b.append(T(ex, py + 360, "20.0x", 56, SIG, 700, font=MONO))
    b.append(f'<path d="M{ex} {py+382} H{ex + 56*0.6*5}" stroke="{SIG}" stroke-width="6"/>')
    b.append(T(px + 70, py + 470, "이 20배는 어디서 왔을까?", 50, TXT, 700))
    # 상태 막대: 의견 분포(그림) — SELL만 숫자
    sy = 3130
    b.append(T(150, sy, "BUY", 34, SUB, 700, font=MONO, ls=4))
    b.append(f'<rect x="270" y="{sy-30}" width="1500" height="30" fill="{DIM}"/>')
    b.append(T(1810, sy, "HOLD", 34, SUB, 700, font=MONO, ls=4))
    b.append(f'<rect x="1950" y="{sy-30}" width="110" height="30" fill="{FAINT}"/>')
    b.append(T(2330, sy, "SELL 0.0%", 34, SIG, 700, "end", font=MONO, ls=2))
    b.append(T(150, sy + 70, "※ 설명을 위한 가상의 화면", 30, DIM, 500))

    # 아래: 저자·출판사
    b.append(f'<path d="M150 3330 H2330" stroke="{EDGE}" stroke-width="4"/>')
    b.append(T(150, 3480, "호차차 지음", 72, TXT, 800))
    aw = tw("호차차 지음", 72)
    b.append(f'<path d="M{150+aw+40} 3426 V3486" stroke="{DIM}" stroke-width="4"/>')
    b.append(T(150 + aw + 80, 3480, "유페이퍼", 52, SUB, 700, ls=4))
    b.append(T(2330, 3480, "AI READING SERIES 05", 34, DIM, 500, "end", font=MONO, ls=6))

    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{"".join(b)}</svg>'
    big = IMG / "book5_cover_2x.png"
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(big), output_width=W, output_height=H)
    out = IMG / "book5_cover.png"
    Image.open(big).convert("RGB").resize((1240, 1835), Image.LANCZOS).save(out)
    return out

if __name__ == "__main__":
    print(build())
