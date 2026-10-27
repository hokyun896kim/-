#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""미리보기 샘플 PDF: 본문 PDF의 앞부분(표지~1장) + 구매 안내(CTA) 페이지.
책별 내용은 content 모듈의 SAMPLE 사전으로 바꾼다(없으면 1권 값). BOOK=content3 python sample_pdf.py"""
import io, os, importlib, pathlib
from pypdf import PdfReader, PdfWriter
from weasyprint import HTML
C = importlib.import_module(os.environ.get('BOOK', 'content'))

ROOT=pathlib.Path(__file__).resolve().parent
BUILD=ROOT/"build"
SRC=BUILD/getattr(C, "PDF_OUT", "preview.pdf")
S=getattr(C, "SAMPLE", {})
OUT=BUILD/S.get("out", "sample.pdf")
COL=S.get("colors", {"g1":"#102B39","g2":"#163B4E","g3":"#23596F","gold":"#C0894B","goldl":"#E9C892",
                     "glow":"rgba(192,137,75,.30)","edge":"rgba(192,137,75,.5)","lead":"#D9E4E8","toc":"#EAF0F2","foot":"#9FB4BC"})

def css():
    return f"""
@page{{size:152mm 225mm;margin:0}}
*{{margin:0;box-sizing:border-box}}
body{{font-family:"Noto Sans CJK KR",sans-serif}}
.cta{{width:152mm;height:225mm;background:linear-gradient(160deg,{COL['g1']},{COL['g2']} 55%,{COL['g3']});
 color:#fff;padding:26mm 18mm;display:flex;flex-direction:column;position:relative;overflow:hidden}}
.cta::before{{content:"";position:absolute;right:-30mm;top:-30mm;width:110mm;height:110mm;border-radius:50%;
 background:radial-gradient(circle,{COL['glow']},transparent 70%)}}
.eyebrow{{letter-spacing:.35em;font-size:10pt;color:{COL['gold']};font-weight:700;margin-bottom:auto}}
h1{{font-size:24pt;font-weight:800;line-height:1.4;margin:0 0 6mm}}
.rule{{width:24mm;height:3px;background:{COL['gold']};margin:0 0 7mm}}
.lead{{font-size:11pt;color:{COL['lead']};line-height:1.8;margin-bottom:8mm}}
.toc{{font-size:10.5pt;color:{COL['toc']};line-height:1.95}}
.toc b{{color:{COL['goldl']};font-weight:700}}
.buy{{margin-top:auto;background:rgba(255,255,255,.06);border:1px solid {COL['edge']};
 border-radius:10px;padding:6mm 6mm}}
.buy .t{{font-size:11pt;font-weight:800;color:#fff;margin-bottom:2mm}}
.buy .m{{font-size:10pt;color:{COL['goldl']}}}
.foot{{margin-top:6mm;font-size:9pt;color:{COL['foot']}}}
"""

LEAD1='"이 종목 살까요?"가 아니라<br>"지금 무엇을 확인해야 하지?"로.<br>나머지 이야기는 본문에서 이어집니다.'
TOC1=["프롤로그 · 1~19장 · 에필로그","1부 나는 왜 계속 흔들렸는가","2부 질문이 바뀌자 투자가 바뀌었다",
      "3부 AI를 투자위원회로 만들기 시작하다","4부 계좌를 키운 것은 매수 버튼이 아니었다","5부 실전에서 가장 먼저 달라진 것들",
      "6부 독자가 오늘 바로 써볼 수 있는 질문들","부록 A~E · AI 투자 질문 20개 / 장전·장마감 체크리스트 / 매수·매도 전 10문항"]

def cta_html():
    toc="<br>\n    ".join(S.get("toc", TOC1))
    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><style>{css()}</style></head>
<body><div class="cta">
  <div class="eyebrow">PREVIEW</div>
  <h1>여기까지가<br>미리보기입니다</h1>
  <div class="rule"></div>
  <div class="lead">{S.get("lead", LEAD1)}</div>
  <div class="toc">
    <b>전체 구성</b><br>
    {toc}
  </div>
  <div class="buy">
    <div class="t">전체 보기 · 구매 문의</div>
    <div class="m">{C.EMAIL}</div>
  </div>
  <div class="foot">『{C.TITLE}』 · 호차차 지음 · {S.get("foot", "종목 추천·수익 보장 아님(투자 교육·실전 기록)")}</div>
</div></body></html>"""

def last_page(src):
    """표지~1장 끝 쪽 수: SAMPLE['last'] 지정값, 없으면 PDF 북마크에서 ‘2장.’ 시작 쪽 바로 앞."""
    if "last" in S: return S["last"]
    def walk(o):
        for it in o:
            if isinstance(it, list): yield from walk(it)
            else: yield it
    for it in walk(src.outline):
        if it.title.startswith("2장."): return src.get_destination_page_number(it)   # 0부터 → 그대로 ‘앞쪽 수’
    return 17

def build():
    cta_bytes=io.BytesIO(); HTML(string=cta_html(), base_url=str(ROOT)).write_pdf(cta_bytes)
    cta=PdfReader(cta_bytes)
    src=PdfReader(str(SRC))
    last=last_page(src)
    w=PdfWriter()
    if S.get("rerender"):
        # 앞부분만 다시 렌더링 → 폰트에 실제로 쓴 글자만 담겨 용량이 작다(본문 PDF와 같은 레이아웃)
        import build_preview
        doc=HTML(string=build_preview.render(write=False), base_url=str(ROOT)).render()
        part=io.BytesIO(); doc.copy(doc.pages[:last]).write_pdf(part)
        for pg in PdfReader(part).pages: w.add_page(pg)
    else:                         # 잠긴 책(1권): 완성본 PDF에서 쪽을 그대로 복사
        for i in range(last): w.add_page(src.pages[i])
    w.add_page(cta.pages[0])
    w.add_metadata({"/Title":f"{C.TITLE} (미리보기)","/Author":C.AUTHOR,
                    "/Subject":"미리보기 — 표지·프롤로그·1장","/Keywords":S.get("keywords","AI 투자, 주식투자, 미리보기")})
    with open(OUT,"wb") as f: w.write(f)
    print("[ok] 샘플 PDF →", OUT, f"({last+1}쪽)")

if __name__=="__main__": build()
