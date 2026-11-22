# -*- coding: utf-8 -*-
"""
4권 『공시는 뉴스보다 먼저 말한다』 표지.
방향: 흰 종이 + 먹색 + 형광 노랑 한 줄. ①~③권(2권 크림·선 그림, 3권 먹색 바탕·금색)과 겹치지 않게.
그림: 회색으로 흐려진 뉴스 기사(11:47) 위에 선명한 공시 원문(접수 08:31)이 놓여 있고,
      원문 표의 한 줄(계약 기간)에만 형광펜이 그어져 있다 — '뉴스보다 먼저', '한 줄의 무게'.
필수 글자: 제목·저자명·출판사명(유페이퍼)·시리즈. 산출: build/img/book4_cover.png (1240×1835), _2x
"""
import pathlib, random, cairosvg
from PIL import Image, ImageChops, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent
IMG = ROOT / "build" / "img"; IMG.mkdir(parents=True, exist_ok=True)
W, H = 2480, 3670
SANS, SERIF = "Noto Sans CJK KR", "Noto Serif CJK KR"
PAPER, INK, GREY, LIGHT, RULE, HI = "#FAFAF7", "#1D1D1F", "#8C8C88", "#C9C9C4", "#E2E1DB", "#F2D200"
BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"

def T(x, y, s, size, fill=INK, w=700, anchor="start", font=SANS, ls=0, op=1):
    return (f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" font-weight="{w}" fill="{fill}" '
            f'text-anchor="{anchor}" letter-spacing="{ls}" opacity="{op}">{s}</text>')

def tw(s, size):
    return ImageFont.truetype(BOLD, size, index=1).getlength(s)

def lines(x, y, widths, gap, h, col, op=1):
    return [f'<rect x="{x}" y="{y+i*gap}" width="{w}" height="{h}" rx="{h/2}" fill="{col}" opacity="{op}"/>'
            for i, w in enumerate(widths)]

def build():
    rnd = random.Random(4)
    b = [f'<rect width="{W}" height="{H}" fill="{PAPER}"/>']
    # 머리글
    b.append(T(150, 200, "DART · 공시 · AI", 46, INK, 800, ls=10))
    b.append(T(2330, 200, "호차차의 AI 읽기 ④", 42, GREY, 700, "end"))
    b.append(f'<path d="M150 250 H2330" stroke="{INK}" stroke-width="4"/>')
    # 제목(명조, 왼쪽 정렬) — '먼저'에 형광펜
    b.append(T(140, 560, "공시는", 250, INK, 900, font=SERIF, ls=-6))
    b.append(T(140, 840, "뉴스보다", 250, INK, 900, font=SERIF, ls=-6))
    w_m = tw("먼저", 250) * 1.02
    b.append(f'<path d="M140 1060 L{150+w_m:.0f} 1048 L{150+w_m:.0f} 1132 L144 1140 Z" fill="{HI}"/>')
    b.append(T(140, 1120, "먼저 말한다", 250, INK, 900, font=SERIF, ls=-6))
    b.append(T(150, 1250, "AI와 함께 읽는 DART 공시,", 58, INK, 500))
    b.append(T(150, 1332, "기업이 직접 쓴 한 줄의 무게", 58, INK, 500))

    # ── 그림 ① 뒤쪽: 흐려진 뉴스 기사(늦게 나온 해석)
    nx, ny = 1060, 1520
    b.append(f'<g transform="rotate(4 {nx+600} {ny+700})" opacity=".55">')
    b.append(f'<rect x="{nx}" y="{ny}" width="1200" height="1460" fill="#FFFFFF" stroke="{LIGHT}" stroke-width="4"/>')
    b.append(T(nx + 70, ny + 120, "뉴스 · 11:47", 40, GREY, 700, ls=4))
    b += lines(nx + 70, ny + 190, [1000, 860], 92, 54, GREY, .7)                 # 굵은 제목 두 줄
    b.append(T(nx + 70, ny + 430, "“대규모 공급계약… 매출 30% 규모”", 46, GREY, 700))
    b += lines(nx + 70, ny + 520, [rnd.randint(820, 1060) for _ in range(9)], 64, 22, LIGHT)
    b.append('</g>')

    # ── 그림 ② 앞쪽: 선명한 공시 원문(먼저 올라온 원본)
    dx, dy, dw = 220, 1660, 1220
    b.append(f'<rect x="{dx+18}" y="{dy+18}" width="{dw}" height="1420" fill="{RULE}"/>')   # 종이 두께(그림자 대신 평면 오프셋)
    b.append(f'<rect x="{dx}" y="{dy}" width="{dw}" height="1420" fill="#FFFFFF" stroke="{INK}" stroke-width="5"/>')
    b.append(T(dx + 70, dy + 120, "공시 원문 · 접수 08:31", 42, INK, 800, ls=3))
    b.append(T(dx + 70, dy + 210, "단일판매ㆍ공급계약체결", 60, INK, 900))
    b.append(f'<path d="M{dx+70} {dy+260} H{dx+dw-70}" stroke="{INK}" stroke-width="3"/>')
    rows = [("계약금액", "120억 원"), ("최근 매출액", "400억 원"), ("매출액 대비", "30%"),
            ("계약기간", "2년"), ("계약상대방", "국내 ○○사"), ("기타 투자판단", "…")]
    for i, (k, v) in enumerate(rows):
        y = dy + 360 + i * 150
        if k == "계약기간":     # 형광펜 한 줄 — 이 책의 시그니처
            b.append(f'<rect x="{dx+50}" y="{y-80}" width="{dw-100}" height="108" fill="{HI}"/>')
        b.append(T(dx + 80, y, k, 52, INK, 700))
        b.append(T(dx + dw - 80, y, v, 52, INK, 800, "end"))
        b.append(f'<path d="M{dx+70} {y+44} H{dx+dw-70}" stroke="{RULE}" stroke-width="3"/>')
    b.append(T(dx + 70, dy + 1350, "※ 설명을 위한 가상의 공시", 36, GREY, 500))

    # ── 아래: 저자·출판사·스티커
    b.append(f'<path d="M150 3330 H2330" stroke="{INK}" stroke-width="4"/>')
    b.append(T(150, 3480, "호차차 지음", 72, INK, 800))
    aw = tw("호차차 지음", 72)
    b.append(f'<path d="M{150+aw+40} 3426 V3486" stroke="{GREY}" stroke-width="4"/>')
    b.append(T(150 + aw + 80, 3480, "유페이퍼", 52, GREY, 700, ls=4))
    st = "AI 질문 카드 31개 수록"; sw = tw(st, 44) + 80
    b.append(f'<rect x="{2330-sw}" y="3408" width="{sw}" height="100" fill="{HI}"/>')
    b.append(T(2330 - sw / 2, 3474, st, 44, INK, 800, "middle"))

    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{"".join(b)}</svg>'
    big = IMG / "book4_cover_2x.png"
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(big), output_width=W, output_height=H)
    im = Image.open(big).convert("RGB")                      # 옅은 종이 질감
    noise = Image.effect_noise((W, H), 14).convert("RGB")
    im = ImageChops.blend(im, ImageChops.multiply(im, noise.point(lambda v: 225 + v * 30 // 255)), 0.3)
    im.save(big)
    out = IMG / "book4_cover.png"
    im.resize((1240, 1835), Image.LANCZOS).save(out)
    return out

if __name__ == "__main__":
    print(build())
