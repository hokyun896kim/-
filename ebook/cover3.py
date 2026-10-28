# -*- coding: utf-8 -*-
"""
3권 『나는 유튜브 매매법을 믿지 않았다』 표지 — ‘유튜브 매매법의 벽’.
2권 표지와 같은 틀(크림 종이, 굵은 검정 제목, [ ] 머리글, 작은 사람 한 명, 그림 하나)에 포인트 색만 초록.
그림: 유튜브 썸네일로 쌓인 벽(저자 표지의 매매법 이름 그대로) — 대부분 X로 지워지고, 살아남은 4장만 초록.
왼쪽의 작은 사람이 돋보기로 벽을 들여다본다.
산출: build/img/book3_cover.png (1240×1835). 2배 크기 SVG → 축소 + 종이 질감.
"""
import pathlib, cairosvg
from PIL import Image, ImageFont, ImageChops

ROOT = pathlib.Path(__file__).resolve().parent
IMG = ROOT / "build" / "img"; IMG.mkdir(parents=True, exist_ok=True)

W, H = 2480, 3670
SANS, SERIF = "Noto Sans CJK KR", "Noto Serif CJK KR"
PAPER, INK, NAVY, GREEN, GREEND, MUTE = "#F3EEE3", "#1B1B1B", "#22304D", "#2E7D5B", "#1F5E43", "#7A7468"

# 5×5 벽: (문구, 살아남음 여부) — 이름은 저자 표지의 매매법 그대로
WALL = [
    [("승률 90% 매매법", 0), ("급락 반등", 1), ("급등주 공식", 0), ("거래량 폭발 종목", 0), ("돌파 매매 비법", 0)],
    [("정배열 필승법", 0), ("손절 5% 원칙", 0), ("세력 매집 신호", 0), ("외국인 따라잡기", 0), ("정배열 눌림목", 1)],
    [("골든크로스 매수", 0), ("볼린저 돌파", 0), ("지수 과매도", 1), ("하루 10% 단타", 0), ("상한가 따라잡기", 0)],
    [("주도주 추격", 0), ("신고가 매매", 0), ("5분봉 스캘핑", 0), ("장대양봉 매수", 0), ("차트 하나로 끝", 0)],
    [("100% 수익 공식", 0), ("RSI 70 매도", 0), ("시초가 매매", 0), ("파는 규칙", 1), ("테마주 순환매", 0)],
]

def T(x, y, s, size, fill=INK, w=700, anchor="middle", ls=0, font=SANS, op=1):
    return (f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" font-weight="{w}" fill="{fill}" '
            f'text-anchor="{anchor}" letter-spacing="{ls}" opacity="{op}">{s}</text>')

def text_w(t, size, weight="Bold"):
    return ImageFont.truetype(f"/usr/share/fonts/opentype/noto/NotoSansCJK-{weight}.ttc", size, index=1).getlength(t)

def card(x, y, w, h, label, alive):
    tx, ty, tw, th = x+16, y+16, w-32, h-92
    if alive:
        pts = f"{tx+26},{ty+th-26} {tx+tw*.32},{ty+th*.62} {tx+tw*.55},{ty+th*.55} {tx+tw*.78},{ty+th*.30} {tx+tw-30},{ty+24}"
        return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="20" fill="{GREEN}"/>'
                f'<rect x="{tx}" y="{ty}" width="{tw}" height="{th}" rx="12" fill="{GREEND}"/>'
                f'<polyline points="{pts}" fill="none" stroke="{PAPER}" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>'
                f'<circle cx="{x+w-30}" cy="{y+30}" r="34" fill="{PAPER}"/>'
                f'<path d="M{x+w-46} {y+30} l11 12 l20 -24" fill="none" stroke="{GREEN}" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>'
                + T(x+w/2, y+h-28, label, 38, PAPER, 900))
    pts = f"{tx+20},{ty+th*.30} {tx+tw*.30},{ty+th*.42} {tx+tw*.50},{ty+th*.36} {tx+tw*.72},{ty+th*.66} {tx+tw-20},{ty+th*.78}"
    cx, cy = tx+tw/2, ty+th/2
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="20" fill="{PAPER}" stroke="{NAVY}" stroke-width="5" opacity=".75"/>'
            f'<rect x="{tx}" y="{ty}" width="{tw}" height="{th}" rx="12" fill="#E2DCCF"/>'
            f'<polyline points="{pts}" fill="none" stroke="{NAVY}" stroke-width="6" stroke-linejoin="round" opacity=".35"/>'
            f'<path d="M{cx-18} {cy-24} L{cx+26} {cy} L{cx-18} {cy+24} Z" fill="{NAVY}" opacity=".40"/>'
            + T(x+w/2, y+h-30, label, 31, NAVY, 700, op=.62)
            + f'<path d="M{x+14} {y+h-14} L{x+w-14} {y+14}" stroke="{NAVY}" stroke-width="5" stroke-linecap="round" opacity=".55"/>')

def inspector(x, y, s=1.0, col=GREEN):
    """돋보기를 든 사람(옆모습 실루엣). (x, y)=발 기준."""
    return (f'<g transform="translate({x},{y}) scale({s})" fill="{NAVY}" stroke="{NAVY}" stroke-linecap="round" stroke-linejoin="round">'
            f'<circle cx="4" cy="-262" r="30" stroke="none"/>'
            f'<path d="M-26 -222 Q-4 -234 24 -222 Q32 -160 26 -104 L-24 -104 Q-34 -160 -26 -222 Z" stroke="none"/>'
            f'<path d="M-10 -106 L-14 -4" stroke-width="26" fill="none"/><path d="M12 -106 L18 -4" stroke-width="26" fill="none"/>'
            f'<path d="M-24 0 H6 M8 0 H40" stroke-width="14" fill="none"/>'
            f'<path d="M-22 -206 L-30 -130" stroke-width="17" fill="none"/>'
            f'<path d="M18 -208 L66 -214 L96 -250" stroke-width="17" fill="none"/>'            # 앞으로 뻗은 팔
            f'<circle cx="124" cy="-282" r="40" fill="{PAPER}" stroke="{col}" stroke-width="13"/>'  # 돋보기 렌즈
            f'<path d="M98 -254 L80 -232" stroke="{col}" stroke-width="15" fill="none"/>'
            f'</g>')

def build():
    b = [f'<rect width="{W}" height="{H}" fill="{PAPER}"/>']
    # 시리즈 표기(작게) + 머리글 — 2권과 같은 자리
    b.append(T(150, 175, "호차차의 AI 읽기 ②", 46, NAVY, 800, "start"))
    b.append(f'<path d="M150 205 H560" stroke="{NAVY}" stroke-width="4"/>')
    b.append(T(W/2, 330, "[  그 매매법, 정말 통했을까?  ]", 66, GREEN, 800, ls=10))
    # ── 그림: 썸네일 벽 + 땅 + 돋보기 든 사람
    gx0, gy0, gx1, gy1, gap = 640, 450, 2330, 1880, 26
    cw = (gx1 - gx0 - 4*gap) / 5; ch = (gy1 - gy0 - 4*gap) / 5
    alive = []
    for r, row in enumerate(WALL):
        for c, (label, ok) in enumerate(row):
            x = gx0 + c*(cw+gap); y = gy0 + r*(ch+gap)
            (alive if ok else b).append(card(x, y, cw, ch, label, ok))
    b += alive
    b.append(f'<path d="M150 1930 H2330" stroke="{NAVY}" stroke-width="6" opacity=".45"/>')
    b.append(f'<ellipse cx="380" cy="1932" rx="70" ry="10" fill="{NAVY}" opacity=".18"/>')
    b.append(inspector(380, 1928, 1.25))
    # ── 제목·부제·지은이
    b.append(T(W/2, 2250, "나는 유튜브", 230, INK, 900, ls=-8))
    b.append(T(W/2, 2490, "매매법을", 230, INK, 900, ls=-8))
    b.append(T(W/2, 2730, "믿지 않았다", 230, INK, 900, ls=-8))
    b.append(T(W/2, 2880, "AI와 함께 21년 치 데이터로 돌려봤더니, 살아남은 건 몇 개뿐이었다", 54, MUTE, 600, font=SERIF))
    aw = text_w("호차차 지음", 54)
    b.append(f'<path d="M520 2995 H{W/2-aw/2-40} M{W/2+aw/2+40} 2995 H1960" stroke="{INK}" stroke-width="3"/>')
    b.append(T(W/2, 3014, "호차차 지음", 54, INK, 700))
    # ── 인용(프롤로그) + 데이터 한 줄
    b.append(T(W/2, 3220, "“그 방법, 정말 통했어? 숫자로 보여 줘.”", 76, INK, 600, font=SERIF))
    b.append(T(W/2, 3315, "2006~2026 · 상장폐지 983개 포함 · 신호 조합 1,854개 검증", 48, MUTE, 500, font=SERIF))
    # 작은 원형 스티커
    sx, sy = 2140, 3500
    b.append(f'<circle cx="{sx}" cy="{sy}" r="128" fill="{PAPER}" stroke="{NAVY}" stroke-width="6"/>')
    b.append(T(sx, sy-36, "실전 규칙", 42, NAVY, 800) + T(sx, sy+30, "카드 4종", 58, GREEN, 900) + T(sx, sy+82, "수록", 38, NAVY, 800))
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{"".join(b)}</svg>'
    big = IMG / "book3_cover_2x.png"
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(big), output_width=W, output_height=H)
    im = Image.open(big).convert("RGB")                       # 종이 질감(2권과 같게)
    noise = Image.effect_noise((W, H), 18).convert("RGB")
    im = ImageChops.blend(im, ImageChops.multiply(im, noise.point(lambda v: 210 + v*45//255)), 0.35)
    im.save(big)
    out = IMG / "book3_cover.png"
    im.resize((1240, 1835), Image.LANCZOS).save(out)
    return out

if __name__ == "__main__":
    print(build())
