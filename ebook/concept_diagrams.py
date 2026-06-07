# -*- coding: utf-8 -*-
"""
개념 도식(설명 삽화) ― 본문 중간에 들어가 내용 이해를 돕는 '그려진 그림'.
SVG로 그린 뒤 PNG로 렌더(한글 라벨 포함). 산출: build/img/fig_<n>.png
※ 스타일 검증용으로 우선 1·5·6장 제작. 확정 후 전 장으로 확장.
"""
import pathlib, cairosvg

IMG=(pathlib.Path(__file__).resolve().parent/"build"/"img"); IMG.mkdir(parents=True,exist_ok=True)
NAVY="#163B4E"; NAVY2="#21566E"; ACCENT="#C0894B"; ACCENTD="#9C6B33"
INK="#2B2724"; MUT="#6E6A63"; CREAM="#F7F2E8"; LINE="#E1D9C9"
GOOD="#2F6F5E"; GOODBG="#EAF1ED"; BAD="#A6433B"; BADBG="#F7EEE8"; FONT="Noto Sans CJK KR"

def _png(name, svg, w, h, scale=2.4):
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(IMG/f"{name}.png"),
                     output_width=int(w*scale), output_height=int(h*scale))

def _frame(w,h):
    return (f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="14" fill="{CREAM}" stroke="{LINE}" stroke-width="1.5"/>')

def fig_pendulum():  # 1장 — 감정의 진자
    W,H=900,360
    px,py=450,70
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       _frame(W,H),
       f'<text x="{W/2}" y="46" font-family="{FONT}" font-size="22" font-weight="700" fill="{NAVY}" text-anchor="middle">감정의 진자</text>',
       # 스윙 범위 호(점선)
       f'<path d="M250 300 A220 220 0 0 1 650 300" fill="none" stroke="{LINE}" stroke-width="2" stroke-dasharray="5 6"/>',
       # 좌/우 점선 팔
       f'<line x1="{px}" y1="{py}" x2="255" y2="295" stroke="{BAD}" stroke-width="2" stroke-dasharray="4 6" opacity="0.6"/>',
       f'<line x1="{px}" y1="{py}" x2="645" y2="295" stroke="{ACCENTD}" stroke-width="2" stroke-dasharray="4 6" opacity="0.6"/>',
       # 중앙 팔 + 추
       f'<line x1="{px}" y1="{py}" x2="{px}" y2="300" stroke="{NAVY}" stroke-width="4"/>',
       f'<circle cx="{px}" cy="{py}" r="6" fill="{NAVY}"/>',
       f'<circle cx="{px}" cy="305" r="34" fill="{NAVY}"/>',
       f'<text x="{px}" y="312" font-family="{FONT}" font-size="20" font-weight="700" fill="#fff" text-anchor="middle">나</text>',
       # 좌우 라벨
       f'<circle cx="200" cy="250" r="40" fill="{BADBG}" stroke="{BAD}" stroke-width="1.5"/>',
       f'<text x="200" y="245" font-family="{FONT}" font-size="19" font-weight="700" fill="{BAD}" text-anchor="middle">공포</text>',
       f'<text x="200" y="268" font-family="{FONT}" font-size="12" fill="{MUT}" text-anchor="middle">못 산다</text>',
       f'<circle cx="700" cy="250" r="40" fill="#F6EEDD" stroke="{ACCENTD}" stroke-width="1.5"/>',
       f'<text x="700" y="245" font-family="{FONT}" font-size="19" font-weight="700" fill="{ACCENTD}" text-anchor="middle">욕심</text>',
       f'<text x="700" y="268" font-family="{FONT}" font-size="12" fill="{MUT}" text-anchor="middle">못 판다</text>',
       f'<text x="{W/2}" y="348" font-family="{FONT}" font-size="14" fill="{INK}" text-anchor="middle">기준이 없으면, 시장이 아니라 내 감정에 휘둘린다.</text>',
       '</svg>']
    _png("fig_1","".join(s),W,H)

def fig_company_stock():  # 5장 — 좋은 기업 ≠ 좋은 주식
    W,H=900,360
    def chart(x,title,sub,line,dot=None,color=NAVY):
        g=[f'<text x="{x+130}" y="40" font-family="{FONT}" font-size="17" font-weight="700" fill="{NAVY}" text-anchor="middle">{title}</text>',
           f'<text x="{x+130}" y="60" font-family="{FONT}" font-size="12" fill="{MUT}" text-anchor="middle">{sub}</text>',
           f'<line x1="{x+20}" y1="90" x2="{x+20}" y2="270" stroke="{MUT}" stroke-width="2"/>',
           f'<line x1="{x+20}" y1="270" x2="{x+250}" y2="270" stroke="{MUT}" stroke-width="2"/>',
           f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>']
        if dot: g.append(f'<circle cx="{dot[0]}" cy="{dot[1]}" r="7" fill="{ACCENT}"/>'
                         f'<text x="{dot[0]}" y="{dot[1]-14}" font-family="{FONT}" font-size="12" font-weight="700" fill="{ACCENTD}" text-anchor="middle">지금</text>')
        return "".join(g)
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       _frame(W,H),
       chart(30,"좋은 기업 (사업 가치)","실적이 꾸준히 우상향",
             "50,260 110,235 170,205 230,175 270,150", color=GOOD),
       chart(470,"좋은 주식? (가격)","이미 기대가 선반영됨",
             "490,255 540,250 580,150 620,120 700,128 740,132",
             dot=(620,120), color=BAD),
       # 가운데 ≠
       f'<circle cx="{W/2}" cy="180" r="26" fill="#fff" stroke="{ACCENT}" stroke-width="2"/>',
       f'<text x="{W/2}" y="190" font-family="{FONT}" font-size="24" font-weight="800" fill="{ACCENTD}" text-anchor="middle">≠</text>',
       f'<text x="{W/2}" y="342" font-family="{FONT}" font-size="14" fill="{INK}" text-anchor="middle">좋은 기업이라도, 기대가 이미 가격에 반영됐다면 좋은 주식이 아니다.</text>',
       '</svg>']
    _png("fig_5","".join(s),W,H)

def fig_funnel():  # 6장 — 시장 → 섹터 → 종목
    W,H=900,360
    rows=[("시장","위험선호인가, 위험회피인가 — 가장 큰 방향",120,820,NAVY),
          ("섹터","돈이 지금 어느 업종으로 이동하는가",210,730,NAVY2),
          ("종목","그 흐름 안에서 비로소 고른다",320,620,ACCENTD)]
    s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       _frame(W,H),
       f'<text x="{W/2}" y="46" font-family="{FONT}" font-size="22" font-weight="700" fill="{NAVY}" text-anchor="middle">돈은 위에서 아래로 흐른다</text>']
    y=70
    for i,(t,d,x1,x2,c) in enumerate(rows):
        yy=y+i*88
        s.append(f'<path d="M{x1} {yy} H{x2} L{x2-55} {yy+66} H{x1+55} Z" fill="{c}" opacity="{0.92-i*0.07}"/>')
        s.append(f'<text x="{W/2}" y="{yy+30}" font-family="{FONT}" font-size="20" font-weight="800" fill="#fff" text-anchor="middle">{t}</text>')
        s.append(f'<text x="{W/2}" y="{yy+52}" font-family="{FONT}" font-size="12.5" fill="#EAF0F2" text-anchor="middle">{d}</text>')
        if i<2: s.append(f'<path d="M{W/2} {yy+70} l-9 -2 9 14 9 -14 z" fill="{ACCENT}"/>')
    s.append('</svg>')
    _png("fig_6","".join(s),W,H)

def build():
    fig_pendulum(); fig_company_stock(); fig_funnel()
    print("[ok] concept figures: fig_1, fig_5, fig_6")

if __name__=="__main__":
    build()
