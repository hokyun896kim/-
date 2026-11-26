# -*- coding: utf-8 -*-
"""4·5권 인스타 카드뉴스 — 1080×1350(2배 2160×2700으로 그려 저장). 표지와 같은 색·글꼴.
원칙(design.md 홍보물): 한 장에 서체 2개, 밝은 요소 1개, CTA 1개, 느낌표·과장어 없음, 숫자는 책 원고에 있는 것만(must_be_in).
산출: promo/cards/book4_01.png … book5_06.png"""
import base64, pathlib, cairosvg
from PIL import ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "promo" / "cards"; OUT.mkdir(parents=True, exist_ok=True)
MD4 = (ROOT / "source" / "book4.md").read_text(encoding="utf-8")
MD5 = (ROOT / "source" / "book5.md").read_text(encoding="utf-8")
W, H = 2160, 2700
SANS, SERIF, MONO = "Noto Sans CJK KR", "Noto Serif CJK KR", "JetBrains Mono"
FB = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"

def must_be_in(md, *xs):
    for x in xs: assert x in md, f"원고에 없음: {x}"
def esc(s): return str(s).replace("&", "&amp;").replace("<", "&lt;")
import re as _re
def T(x, y, s, size, fill, w=700, anchor="start", font=SANS, ls=0):
    if font == MONO and _re.search(r"[\uac00-\ud7a3]", str(s)): font = SANS   # 고정폭 글꼴엔 한글 없음
    return f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}" letter-spacing="{ls}">{esc(s)}</text>'
def tw(s, size): return ImageFont.truetype(FB, size, index=1).getlength(str(s))
def R(x, y, w, h, fill, stroke=None, sw=4): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"' + (f' stroke="{stroke}" stroke-width="{sw}"' if stroke else "") + "/>"
def img(path, x, y, w, h):
    b = base64.b64encode(pathlib.Path(path).read_bytes()).decode()
    return f'<image x="{x}" y="{y}" width="{w}" height="{h}" href="data:image/png;base64,{b}"/>'
def save(name, body, bg):
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{R(0,0,W,H,bg)}{"".join(body)}</svg>'
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(OUT / f"{name}.png"), output_width=W, output_height=H)

# ───────── 4권: 흰 종이·먹색·형광 노랑 ─────────
P4, I4, G4, L4, Y4 = "#FAFAF7", "#1D1D1F", "#6E6E6A", "#D9D8D2", "#F2D200"
def frame4(b, n):
    b.append(T(160, 200, "호차차의 AI 읽기 ④", 44, G4, 700))
    b.append(T(2000, 200, f"{n} / 6", 44, G4, 700, "end", MONO))
    b.append(f'<path d="M160 250 H2000" stroke="{I4}" stroke-width="5"/>')
    b.append(T(160, 2560, "『호재일까, 함정일까』", 48, I4, 800))
def hl(b, x, y, s, size):   # 형광펜 한 줄
    b.append(R(x - 8, y - size * 0.62, tw(s, size) + 16, size * 0.5, Y4))

def book4():
    must_be_in(MD4, "2025년 1월 14일", "56.15", "2024-12-13", "2030-12-31", "9% 남짓", "37", "59")
    b = []; frame4(b, 1)
    b.append(T(160, 900, "매출의 절반짜리", 150, I4, 900, font=SERIF, ls=-4))
    hl(b, 160, 1110, "수주,", 150)
    b.append(T(160, 1110, "수주, 정말일까", 150, I4, 900, font=SERIF, ls=-4))
    b.append(T(170, 1320, "뉴스 제목 말고 공시 원문 표의 한 줄로", 64, G4, 500))
    b.append(T(170, 1410, "다시 읽어 봅니다", 64, G4, 500))
    save("book4_01", b, P4)

    b = []; frame4(b, 2)
    b.append(T(160, 560, "점심시간, 증권 앱 알림", 84, I4, 800))
    b.append(R(160, 680, 1840, 520, "#FFFFFF", L4, 5))
    b.append(T(240, 820, "뉴스 · 12:31", 48, G4, 700, font=MONO))
    b.append(T(240, 960, "A사, 대규모 공급계약", 84, I4, 900))
    b.append(T(240, 1080, "… 한 해 매출의 절반 넘어", 84, I4, 900))
    b.append(T(160, 1460, "눌러 보면 주가는 이미 올라 있습니다.", 64, I4, 600))
    b.append(T(160, 1570, "그 소식의 원본은 공시입니다.", 64, I4, 600))
    b.append(T(160, 1760, "※ 장면은 꾸몄고, 공시는 2025년 1월 14일 실제 공시", 44, G4, 500))
    save("book4_02", b, P4)

    b = []; frame4(b, 3)
    b.append(T(160, 470, "공시 원문 표", 84, I4, 800))
    rows = [("계약금액", "약 2조 747억 원"), ("최근 매출액 대비", "56.15%"), ("계약기간", "2024-12-13 ~ 2030-12-31"), ("계약상대", "유럽 소재 제약사")]
    b.append(R(160, 560, 1840, 1240, "#FFFFFF", I4, 6))
    for k, (a, v) in enumerate(rows):
        y = 760 + k * 260
        if k == 2: b.append(R(190, y - 110, 1780, 170, Y4))
        b.append(T(240, y, a, 64, I4, 700)); b.append(T(1920, y, v, 64, I4, 800, "end"))
        b.append(f'<path d="M220 {y+70} H1940" stroke="{L4}" stroke-width="4"/>')
    b.append(T(160, 1990, "기사 제목의 '매출의 절반'은 두 번째 줄에서,", 60, I4, 600))
    b.append(T(160, 2090, "읽을 곳은 세 번째 줄입니다.", 60, I4, 800))
    save("book4_03", b, P4)

    b = []; frame4(b, 4)
    b.append(T(160, 700, "6년이 조금 넘는 기간에", 104, I4, 900, font=SERIF))
    b.append(T(160, 850, "나눠 들어오는 돈", 104, I4, 900, font=SERIF))
    b.append(R(160, 1080, 1840, 140, L4)); b.append(R(160, 1080, 1840 * 0.5615, 140, I4))
    b.append(T(180, 1040, "계약 전체 = 매출의 56.15%", 56, I4, 700))
    b.append(R(160, 1420, 1840, 140, L4)); b.append(R(160, 1420, 1840 * 0.094, 140, Y4))
    b.append(T(180, 1380, "1년으로 나누면", 56, I4, 700)); b.append(T(160 + 1840 * 0.094 + 30, 1515, "9% 남짓", 72, I4, 900))
    b.append(T(160, 1800, "제목의 숫자는 틀리지 않았습니다.", 64, I4, 600))
    b.append(T(160, 1900, "다만 한 줄 아래까지 읽으면 무게가 달라집니다.", 64, I4, 600))
    save("book4_04", b, P4)

    b = []; frame4(b, 5)
    b.append(T(160, 520, "AI에게는 요약 대신 이렇게", 84, I4, 800))
    b.append(R(160, 640, 1840, 820, "#FFFFFF", I4, 6)); b.append(R(160, 640, 1840, 24, Y4))
    q = ["\"이 공시의 계약 금액을 계약 기간으로", "나눠서 1년 기준으로 최근 매출액 대비", "몇 %인지 계산해 줘. 원문의 숫자는", "단위 그대로 옮겨 줘.\""]
    for k, s in enumerate(q): b.append(T(240, 820 + k * 140, s, 70, I4, 600))
    b.append(T(160, 1700, "이런 질문 카드 37개,", 72, I4, 800))
    b.append(T(160, 1810, "유리·불리 체크리스트 59개를 책 끝에 모았습니다.", 60, I4, 600))
    save("book4_05", b, P4)

    b = []; frame4(b, 6)
    b.append(img(ROOT / "publish" / "book4" / "표지_1240x1835.jpg" if False else ROOT / "build" / "img" / "book4_cover.png", 160, 380, 900, 1332))
    b.append(T(1160, 640, "12월 15일", 96, I4, 900))
    b.append(T(1160, 760, "출간", 96, I4, 900))
    b.append(T(1160, 960, "전자책 9,900원", 60, I4, 700))
    for k, s in enumerate(["공급계약·잠정실적·자사주", "유상증자·전환사채·최대주주", "감사의견·정정공시·침묵"]):
        b.append(T(1160, 1160 + k * 90, s, 52, G4, 600))
    b.append(R(160, 1900, 1840, 200, Y4))
    b.append(T(1080, 2025, "링크는 프로필에", 72, I4, 900, "middle"))
    save("book4_06", b, P4)

# ───────── 5권: 검푸른 화면·신호 빨강·고정폭 숫자 ─────────
B5, T5, S5, D5, E5, R5 = "#0D1117", "#EEF1F5", "#AEB7C2", "#5E6875", "#252D38", "#FF4B3E"
def frame5(b, n):
    b.append(T(160, 200, "RESEARCH / TARGET PRICE / AI", 40, S5, 500, font=MONO, ls=6))
    b.append(T(2000, 200, f"{n} / 6", 44, S5, 700, "end", MONO))
    b.append(f'<path d="M160 250 H2000" stroke="{E5}" stroke-width="5"/>')
    b.append(T(160, 2560, "『매수 의견만 있는 나라』", 48, T5, 800))

def book5():
    must_be_in(MD5, "31곳", "28곳", "1.3%", "21.9%", "97.16%", "100,000", "5,000", "20배", "1만 6,000원", "4,000원")
    b = []; frame5(b, 1)
    b.append(T(160, 880, "증권사 리포트에서", 130, T5, 900, ls=-4))
    b.append(T(160, 1060, "'매도',", 130, R5, 900, ls=-4))
    b.append(T(160, 1240, "보신 적 있나요?", 130, T5, 900, ls=-4))
    b.append(T(170, 1440, "의견 한 단어 대신 그 아래 숫자를 읽는 법", 60, S5, 500))
    save("book5_01", b, B5)

    b = []; frame5(b, 2)
    b.append(T(160, 480, "2025년 말 국내 증권사 31곳", 80, T5, 800))
    b.append(T(160, 600, "매도 의견 0%인 곳 28곳", 80, R5, 900))
    s, g = 200, 24
    for i in range(31):
        r, c = divmod(i, 8); x, y = 160 + c * (s + g), 760 + r * (s + g)
        sell = i >= 28
        b.append(R(x, y, s, s, R5 if sell else "#151B23", None if sell else E5, 4))
        b.append(T(x + s / 2, y + s / 2 + 24, "매도" if sell else "0%", 60, B5 if sell else D5, 800, "middle"))
    b.append(T(160, 1780, "매도 의견을 낸 국내 증권사 3곳, 가장 높은 곳도 1.3%", 54, T5, 600))
    b.append(T(160, 1870, "외국계 서울지점 중에는 21.9%인 곳도", 54, T5, 600))
    b.append(T(160, 2020, "출처: 금융투자협회 공시를 인용한 2026년 3월 보도", 40, D5, 500))
    save("book5_02", b, B5)

    b = []; frame5(b, 3)
    b.append(T(160, 560, "그래서 의견 칸 말고", 92, T5, 900))
    b.append(T(160, 700, "가정 칸을 봅니다", 92, T5, 900))
    b.append(R(160, 860, 1840, 760, "#11161D", E5, 5)); b.append(R(160, 860, 1840, 20, R5))
    b.append(T(240, 1000, "TARGET PRICE", 48, D5, 500, font=MONO, ls=8))
    b.append(T(240, 1200, "100,000", 170, T5, 700, font=MONO))
    b.append(T(240, 1360, "= EPS 5,000 × PER", 76, S5, 500, font=MONO))
    b.append(T(240 + 76 * 0.6 * 19, 1360, "20.0x", 76, R5, 700, font=MONO))
    b.append(T(240, 1500, "이 20배는 어디서 왔을까요?", 64, T5, 700))
    b.append(T(160, 1820, "목표주가는 예언이 아니라 계산의 결과입니다.", 60, T5, 600))
    b.append(T(160, 1920, "계산에는 가정이 들어갑니다.", 60, S5, 500))
    save("book5_03", b, B5)

    b = []; frame5(b, 4)
    b.append(T(160, 520, "목표주가 8만 → 10만 원", 88, T5, 900))
    b.append(T(160, 640, "2만 원은 어디서 왔나", 72, S5, 600))
    bars = [("기준 연도 이동", 16000, R5, "1만 6,000원"), ("이익 추정 상향", 4000, T5, "4,000원"), ("배수 변화", 0, D5, "0원")]
    for k, (lab, v, col, s) in enumerate(bars):
        y = 860 + k * 300
        b.append(T(160, y, lab, 60, T5, 700))
        b.append(R(160, y + 40, max(1840 * v / 20000, 8), 120, col))
        b.append(T(2000, y, s, 64, col if col != D5 else S5, 800, "end", MONO if s[0].isdigit() else SANS))
    b.append(T(160, 1860, "80%는 달력이 넘어간 효과.", 64, T5, 800))
    b.append(T(160, 1960, "책에서는 가상의 B사로 처음부터 계산합니다.", 56, S5, 500))
    save("book5_04", b, B5)

    b = []; frame5(b, 5)
    b.append(T(160, 520, "AI에게는 요약 대신 네 칸", 84, T5, 800))
    b.append(R(160, 640, 1840, 1000, "#11161D", E5, 5)); b.append(T(240, 740, "AI  ›  PROMPT", 44, R5, 700, font=MONO, ls=8))
    for k, (a, v, hot) in enumerate([("의견", "매수 유지, 8만 → 10만 원", False), ("근거", "3분기 영업이익 410억 원", False), ("가정", "매출 13% 성장 · 이익률 14.2% · PER 20배", True), ("위험", "리포트에 언급 없음", False)]):
        y = 900 + k * 180
        b.append(T(240, y, a, 60, D5, 800)); b.append(T(460, y, v, 58, R5 if hot else T5, 800 if hot else 600))
    b.append(T(160, 1840, "질문 카드 33개, 체크리스트 45개,", 64, T5, 800))
    b.append(T(160, 1950, "한 장 요약 양식과 15분 읽기 순서를 담았습니다.", 56, S5, 500))
    b.append(T(160, 2060, "※ 예시는 책 3장의 가상 B사 리포트", 40, D5, 500))
    save("book5_05", b, B5)

    b = []; frame5(b, 6)
    b.append(img(ROOT / "build" / "img" / "book5_cover.png", 160, 380, 900, 1332))
    b.append(T(1160, 640, "12월 15일", 96, T5, 900))
    b.append(T(1160, 760, "출간", 96, T5, 900))
    b.append(T(1160, 960, "전자책 8,900원", 60, T5, 700))
    for k, s in enumerate(["목표주가 쪼개기", "리포트 숫자 vs 공시 원문", "도달률 직접 세기"]):
        b.append(T(1160, 1160 + k * 90, s, 52, S5, 600))
    b.append(R(160, 1900, 1840, 200, R5))
    b.append(T(1080, 2025, "링크는 프로필에", 72, B5, 900, "middle"))
    save("book5_06", b, B5)

if __name__ == "__main__":
    book4(); book5()
    print(sorted(p.name for p in OUT.glob("*.png")))
