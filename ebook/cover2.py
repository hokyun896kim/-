# -*- coding: utf-8 -*-
"""
2권 『질문이 바뀌면 경제가 보인다』 표지 — ‘물음표 길’.
그림 하나로 말하는 표지: 커다란 물음표 모양의 길을 직장인 한 사람이 걷고, 길가 표지판은 금리·환율·물가·실적,
물음표의 점은 ₩ 동전(내 돈). 크림 종이 + 남색·주황 두 색, 굵은 검정 제목, 명조 인용, 종이 질감.
(참고한 방향: 2색 선 그림 · 한 가지 시각 콘셉트 · 넉넉한 여백 — 인포그래픽처럼 보이지 않게)
산출: build/img/book2_cover.png (1240×1835). 2배 크기 SVG로 그린 뒤 줄이고 종이 질감을 얹는다.
"""
import pathlib, random, cairosvg
from PIL import Image, ImageFont, ImageChops

ROOT = pathlib.Path(__file__).resolve().parent
IMG = ROOT / "build" / "img"; IMG.mkdir(parents=True, exist_ok=True)

W, H = 2480, 3670
SANS, SERIF = "Noto Sans CJK KR", "Noto Serif CJK KR"
PAPER, INK, NAVY, ORANGE, MUTE = "#F3EEE3", "#1B1B1B", "#22304D", "#D9542B", "#7A7468"

def T(x, y, s, size, fill=INK, w=700, anchor="middle", ls=0, font=SANS):
    return (f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" font-weight="{w}" fill="{fill}" '
            f'text-anchor="{anchor}" letter-spacing="{ls}">{s}</text>')

def text_w(t, size, weight="Bold", serif=False):
    fam = "NotoSerifCJK" if serif else "NotoSansCJK"
    return ImageFont.truetype(f"/usr/share/fonts/opentype/noto/{fam}-{weight}.ttc", size, index=1).getlength(t)

def sign(x, y, label, col, side=1):
    """길가 표지판: 기둥 + 이름판(한쪽으로 살짝)."""
    w = text_w(label, 54) + 64
    px = x if side > 0 else x - w
    return (f'<path d="M{x} {y} V{y-170}" stroke="{NAVY}" stroke-width="9" stroke-linecap="round"/>'
            f'<rect x="{px}" y="{y-250}" width="{w}" height="92" rx="10" fill="{col}"/>'
            + T(px + w/2, y-186, label, 54, PAPER, 800))

def reader(x, y, s=1.0, col=ORANGE):
    """휴대폰으로 뉴스를 보는 직장인(옆모습 실루엣). (x, y)=발 기준."""
    return (f'<g transform="translate({x},{y}) scale({s})" fill="{col}" stroke="{col}" stroke-linecap="round" stroke-linejoin="round">'
            f'<circle cx="6" cy="-262" r="30" stroke="none"/>'                                          # 머리(살짝 숙임)
            f'<path d="M-26 -222 Q-4 -234 24 -222 Q32 -160 26 -104 L-24 -104 Q-34 -160 -26 -222 Z" stroke="none"/>'  # 재킷
            f'<path d="M-10 -106 L-14 -4" stroke-width="26" fill="none"/>'                               # 다리
            f'<path d="M12 -106 L18 -4" stroke-width="26" fill="none"/>'
            f'<path d="M-24 0 H6 M8 0 H40" stroke-width="14" fill="none"/>'                              # 신발
            f'<path d="M18 -206 L44 -160 L50 -214" stroke-width="17" fill="none"/>'                      # 휴대폰 든 팔
            f'<rect x="40" y="-252" width="24" height="40" rx="5" fill="{NAVY}" stroke="none" transform="rotate(12 52 -232)"/>'
            f'<path d="M-22 -206 L-30 -130" stroke-width="17" fill="none"/>'                             # 내린 팔
            f'<rect x="-50" y="-150" width="36" height="46" rx="6" fill="{NAVY}" stroke="none"/>'        # 서류가방
            f'</g>')

def skyline(y0):
    """먼 도시 윤곽(가는 남색 선)."""
    random.seed(7)
    out, x = [], 150
    while x < 2330:
        w = random.choice([110, 140, 170, 90]); h = random.choice([160, 230, 300, 200, 260])
        out.append(f'<rect x="{x}" y="{y0-h}" width="{w}" height="{h}" fill="none" stroke="{NAVY}" stroke-width="5" opacity=".28"/>')
        for wy in range(int(y0-h+30), int(y0-20), 46):
            for wx in range(int(x+20), int(x+w-20), 36):
                if random.random() < .45:
                    out.append(f'<rect x="{wx}" y="{wy}" width="14" height="20" fill="{NAVY}" opacity=".18"/>')
        x += w + random.choice([10, 24, 40])
    return "".join(out)

def build():
    b = [f'<rect width="{W}" height="{H}" fill="{PAPER}"/>']
    # 시리즈 표기(작게) + 머리글
    b.append(T(150, 175, "호차차의 AI 읽기 ③", 46, NAVY, 800, "start"))
    b.append(f'<path d="M150 205 H560" stroke="{NAVY}" stroke-width="4"/>')
    b.append(T(W/2, 330, "[  뉴스가 내 돈이 되는 길을 묻다  ]", 66, ORANGE, 800, ls=10))
    # ── 그림: 먼 도시 + 물음표 길 + ₩ 점 + 표지판 + 걷는 사람
    b.append(skyline(1960))
    b.append(f'<path d="M150 1960 H2330" stroke="{NAVY}" stroke-width="6" opacity=".35"/>')
    road = "M760 1010 C 760 560, 1720 520, 1720 960 C 1720 1250, 1240 1260, 1240 1560 L 1240 1640"
    b.append(f'<path d="{road}" fill="none" stroke="{NAVY}" stroke-width="190" stroke-linecap="round"/>')
    b.append(f'<path d="{road}" fill="none" stroke="{PAPER}" stroke-width="160" stroke-linecap="round"/>')
    b.append(f'<path d="{road}" fill="none" stroke="{ORANGE}" stroke-width="12" stroke-dasharray="46 36"/>')
    # 물음표의 점 = ₩ 동전
    cx, cy = 1240, 1840
    b.append(f'<circle cx="{cx}" cy="{cy}" r="118" fill="{ORANGE}"/>'
             f'<circle cx="{cx}" cy="{cy}" r="92" fill="none" stroke="{PAPER}" stroke-width="8"/>'
             + T(cx, cy+42, "₩", 120, PAPER, 900))
    # 길가 표지판
    b.append(sign(600, 1010, "뉴스", NAVY, -1))
    b.append(sign(980, 640, "금리", ORANGE, -1))
    b.append(sign(1530, 610, "환율", NAVY, 1))
    b.append(sign(1880, 1000, "물가", ORANGE, 1))
    b.append(sign(1110, 1330, "실적", NAVY, -1))
    # 땅 위의 작은 사람: 휴대폰으로 뉴스를 보고, 그 위로 물음표 길이 펼쳐진다
    b.append(f'<ellipse cx="470" cy="1962" rx="70" ry="10" fill="{NAVY}" opacity=".18"/>')
    b.append(reader(470, 1958, 1.15))
    # ── 제목·부제·지은이
    b.append(T(W/2, 2370, "질문이 바뀌면", 250, INK, 900, ls=-8))
    b.append(T(W/2, 2640, "경제가 보인다", 250, INK, 900, ls=-8))
    b.append(T(W/2, 2790, "금리·환율·실적 뉴스를 내 돈의 언어로 번역하는 직장인 AI 경제 루틴", 54, MUTE, 600, font=SERIF))
    aw = text_w("호차차 지음", 54, "Bold")
    b.append(f'<path d="M520 2905 H{W/2-aw/2-40} M{W/2+aw/2+40} 2905 H1960" stroke="{INK}" stroke-width="3"/>')
    b.append(T(W/2, 2924, "호차차 지음", 54, INK, 700))
    # ── 인용(명조) + 작은 문구
    b.append(T(W/2, 3140, "“경제가 어려운 건 당신 탓이 아닙니다.”", 76, INK, 600, font=SERIF))
    b.append(T(W/2, 3240, "지금까지 연결고리를 배울 기회가 없었을 뿐입니다", 50, MUTE, 500, font=SERIF))
    # 작은 원형 스티커(실제 수록 수)
    sx, sy = 2140, 3440
    b.append(f'<circle cx="{sx}" cy="{sy}" r="132" fill="{PAPER}" stroke="{NAVY}" stroke-width="6"/>')
    b.append(T(sx, sy-40, "AI 프롬프트", 40, NAVY, 800) + T(sx, sy+26, "33개", 64, ORANGE, 900) + T(sx, sy+80, "수록", 38, NAVY, 800))
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{"".join(b)}</svg>'
    big = IMG / "book2_cover_2x.png"
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(big), output_width=W, output_height=H)
    # 종이 질감(아주 옅은 노이즈) — 디지털 평면 느낌을 덜기
    im = Image.open(big).convert("RGB")
    noise = Image.effect_noise((W, H), 18).convert("RGB")
    im = ImageChops.blend(im, ImageChops.multiply(im, noise.point(lambda v: 210 + v*45//255)), 0.35)
    im.save(big)
    out = IMG / "book2_cover.png"
    im.resize((1240, 1835), Image.LANCZOS).save(out)
    return out

if __name__ == "__main__":
    print(build())
