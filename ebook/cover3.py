# -*- coding: utf-8 -*-
"""
3권 『나는 유튜브 매매법을 믿지 않았다』 표지 — ‘체(sieve)’.
2권(크림 종이·선 그림·가운데 정렬)과 일부러 다른 방향: 짙은 먹색 바탕, 왼쪽 정렬 명조 제목, 금색 하나.
그림: 수백 개의 작은 재생(▶) 버튼(유튜브 매매법)이 ‘21년 데이터’라는 체에 걸리고,
      아래로 빠져나온 건 금색 ▶ 4개(급락 반등·정배열 눌림목·지수 과매도·파는 규칙)뿐 — 부제를 그대로 그림으로.
머리글은 저자 원래 표지의 ‘AI · BACKTEST · 21 YEARS’.
산출: build/img/book3_cover.png (1240×1835). 2배 크기 SVG → 축소 + 옅은 질감.
"""
import pathlib, random, cairosvg
from PIL import Image, ImageFont, ImageChops

ROOT = pathlib.Path(__file__).resolve().parent
IMG = ROOT / "build" / "img"; IMG.mkdir(parents=True, exist_ok=True)

W, H = 2480, 3670
SANS, SERIF = "Noto Sans CJK KR", "Noto Serif CJK KR"
BG, CREAM, GOLD, GREY, DIM = "#15181F", "#F2EEE6", "#E4B54A", "#9AA0AC", "#5A606C"

# 체 위에 흩어 둘 유튜브 매매법 이름(저자 표지의 이름들) — 작고 흐리게
NOISE = ["승률 90% 매매법", "급등주 공식", "무조건 오르는 패턴", "손절 5% 원칙", "세력 매집 신호", "골든크로스 매수",
         "하루 10% 단타", "상한가 따라잡기", "차트 하나로 끝", "100% 수익 공식", "볼린저 돌파", "거래량 폭발 종목"]
SURVIVE = ["급락 반등", "정배열 눌림목", "지수 과매도", "파는 규칙"]

def T(x, y, s, size, fill=CREAM, w=700, anchor="start", ls=0, font=SANS, op=1):
    return (f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" font-weight="{w}" fill="{fill}" '
            f'text-anchor="{anchor}" letter-spacing="{ls}" opacity="{op}">{s}</text>')

def tri(cx, cy, s, fill, op=1):
    """재생 버튼 삼각형(둥근 모서리 느낌은 stroke-linejoin)."""
    h = s * 0.9
    return (f'<path d="M{cx-s*.42:.1f} {cy-h/2:.1f} L{cx+s*.5:.1f} {cy:.1f} L{cx-s*.42:.1f} {cy+h/2:.1f} Z" '
            f'fill="{fill}" stroke="{fill}" stroke-width="{max(2, s*.12):.1f}" stroke-linejoin="round" opacity="{op}"/>')

def build():
    rnd = random.Random(21)
    b = [f'<rect width="{W}" height="{H}" fill="{BG}"/>']
    # ── 머리글(저자 원래 표지) + 시리즈(작게, 오른쪽)
    b.append(T(150, 200, "AI · BACKTEST · 21 YEARS", 46, GOLD, 800, ls=14))
    b.append(T(2330, 200, "호차차의 AI 읽기 ②", 42, GREY, 700, "end"))
    b.append(f'<path d="M150 250 H2330" stroke="{DIM}" stroke-width="3"/>')
    # ── 제목: 왼쪽 정렬 명조, 마지막 줄만 금색
    b.append(T(140, 560, "나는 유튜브", 240, CREAM, 900, font=SERIF, ls=-6))
    b.append(T(140, 820, "매매법을", 240, CREAM, 900, font=SERIF, ls=-6))
    b.append(T(140, 1080, "믿지 않았다", 240, GOLD, 900, font=SERIF, ls=-6))
    b.append(T(150, 1200, "AI와 함께 21년 치 데이터로 돌려봤더니,", 56, GREY, 500))
    b.append(T(150, 1280, "살아남은 건 몇 개뿐이었다", 56, GREY, 500))
    # ── 그림 ① 체 위: 수많은 ▶ (유튜브 매매법) — 아래로 갈수록 빽빽하게 쌓여 체에 걸림
    top, sieve = 1420, 2330
    step = 74
    for row, y in enumerate(range(top, sieve - 40, step)):
        density = 0.25 + 0.75 * (y - top) / (sieve - top)          # 체에 가까울수록 빽빽
        for x in range(170, 2330, step):
            if rnd.random() < density:
                jx, jy = rnd.uniform(-14, 14), rnd.uniform(-12, 12)
                b.append(tri(x + jx, y + jy, rnd.choice([26, 30, 34, 38]), GREY, rnd.uniform(.18, .55)))
    # 흐린 매매법 이름 몇 개
    spots = [(260, 1500), (1180, 1470), (1880, 1560), (520, 1700), (1500, 1720), (2050, 1850),
             (300, 1930), (980, 1900), (1650, 2030), (640, 2130), (1320, 2160), (1980, 2190)]
    for (x, y), name in zip(spots, NOISE):
        w = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 34, index=1).getlength(name)
        b.append(f'<rect x="{x-14}" y="{y-40}" width="{w+28}" height="54" rx="8" fill="{BG}" opacity=".85"/>')
        b.append(T(x, y, name, 34, GREY, 700, op=.75))
        b.append(f'<path d="M{x-6} {y-12} H{x+w+6}" stroke="{GREY}" stroke-width="3" opacity=".7"/>')   # 지워진 이름
    # ── 그림 ② 체(21년 데이터)
    b.append(f'<rect x="150" y="{sieve}" width="2180" height="56" fill="none" stroke="{CREAM}" stroke-width="5" opacity=".85"/>')
    for x in range(170, 2330, 34):
        b.append(f'<path d="M{x} {sieve} V{sieve+56}" stroke="{CREAM}" stroke-width="3" opacity=".55"/>')
    b.append(T(W/2, sieve + 126, "2006–2026 · 상장폐지 983개 포함 · 신호 조합 1,854개", 40, GREY, 600, "middle", ls=4))
    # ── 그림 ③ 체를 통과한 금색 ▶ 4개 + 이름
    outs = [(470, 2650), (1050, 2790), (1640, 2670), (2120, 2850)]
    for (x, y), name in zip(outs, SURVIVE):
        b.append(f'<path d="M{x} {sieve+165} V{y-70}" stroke="{GOLD}" stroke-width="4" stroke-dasharray="10 14" opacity=".8"/>')   # 문구 아래에서 시작
        b.append(tri(x, y, 96, GOLD))
        b.append(T(x, y + 112, name, 50, CREAM, 800, "middle"))
    # ── 아래: 인용 · 지은이 · 태그
    b.append(f'<path d="M150 3080 H2330" stroke="{DIM}" stroke-width="3"/>')
    b.append(T(150, 3230, "“그 방법, 정말 통했어? 숫자로 보여 줘.”", 64, CREAM, 600, font=SERIF))
    b.append(T(150, 3330, "「나는 AI에게 종목을 묻지 않았다」 두 번째 이야기", 42, GREY, 600))
    b.append(T(150, 3500, "호차차 지음", 72, CREAM, 800))
    tw = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 44, index=1).getlength("실전 규칙 카드 4종 수록") + 70
    b.append(f'<rect x="{2330-tw}" y="3428" width="{tw}" height="96" rx="48" fill="none" stroke="{GOLD}" stroke-width="5"/>')
    b.append(T(2330 - tw/2, 3492, "실전 규칙 카드 4종 수록", 44, GOLD, 800, "middle"))
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{"".join(b)}</svg>'
    big = IMG / "book3_cover_2x.png"
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(big), output_width=W, output_height=H)
    im = Image.open(big).convert("RGB")                       # 옅은 질감(인쇄물 느낌)
    noise = Image.effect_noise((W, H), 22).convert("RGB")
    im = ImageChops.blend(im, ImageChops.screen(im, noise.point(lambda v: v*22//255)), 0.5)
    im.save(big)
    out = IMG / "book3_cover.png"
    im.resize((1240, 1835), Image.LANCZOS).save(out)
    return out

if __name__ == "__main__":
    print(build())
