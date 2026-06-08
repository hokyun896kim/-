#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""미리보기 샘플 PDF: 본문 PDF의 앞부분(표지~1장) + 구매 안내(CTA) 페이지."""
import io, pathlib
from pypdf import PdfReader, PdfWriter
from weasyprint import HTML
import content as C

ROOT=pathlib.Path(__file__).resolve().parent
BUILD=ROOT/"build"
SRC=BUILD/"preview.pdf"
LAST=17            # 표지~1장 끝 페이지
OUT=BUILD/"sample.pdf"

CTA_CSS="""
@page{size:152mm 225mm;margin:0}
*{margin:0;box-sizing:border-box}
body{font-family:"Noto Sans CJK KR",sans-serif}
.cta{width:152mm;height:225mm;background:linear-gradient(160deg,#102B39,#163B4E 55%,#23596F);
 color:#fff;padding:26mm 18mm;display:flex;flex-direction:column;position:relative;overflow:hidden}
.cta::before{content:"";position:absolute;right:-30mm;top:-30mm;width:110mm;height:110mm;border-radius:50%;
 background:radial-gradient(circle,rgba(192,137,75,.30),transparent 70%)}
.eyebrow{letter-spacing:.35em;font-size:10pt;color:#C0894B;font-weight:700;margin-bottom:auto}
h1{font-size:24pt;font-weight:800;line-height:1.4;margin:0 0 6mm}
.rule{width:24mm;height:3px;background:#C0894B;margin:0 0 7mm}
.lead{font-size:11pt;color:#D9E4E8;line-height:1.8;margin-bottom:8mm}
.toc{font-size:10.5pt;color:#EAF0F2;line-height:1.95}
.toc b{color:#E9C892;font-weight:700}
.buy{margin-top:auto;background:rgba(255,255,255,.06);border:1px solid rgba(192,137,75,.5);
 border-radius:10px;padding:6mm 6mm}
.buy .t{font-size:11pt;font-weight:800;color:#fff;margin-bottom:2mm}
.buy .m{font-size:10pt;color:#E9C892}
.foot{margin-top:6mm;font-size:9pt;color:#9FB4BC}
"""

def cta_html():
    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><style>{CTA_CSS}</style></head>
<body><div class="cta">
  <div class="eyebrow">PREVIEW</div>
  <h1>여기까지가<br>미리보기입니다</h1>
  <div class="rule"></div>
  <div class="lead">"이 종목 살까요?"가 아니라<br>"지금 무엇을 확인해야 하지?"로.<br>나머지 이야기는 본문에서 이어집니다.</div>
  <div class="toc">
    <b>전체 구성</b><br>
    프롤로그 · 1~19장 · 에필로그<br>
    1부 나는 왜 계속 흔들렸는가<br>
    2부 질문이 바뀌자 투자가 바뀌었다<br>
    3부 AI를 투자위원회로 만들기 시작하다<br>
    4부 계좌를 키운 것은 매수 버튼이 아니었다<br>
    5부 실전에서 가장 먼저 달라진 것들<br>
    6부 독자가 오늘 바로 써볼 수 있는 질문들<br>
    부록 A~E · AI 투자 질문 20개 / 장전·장마감 체크리스트 / 매수·매도 전 10문항
  </div>
  <div class="buy">
    <div class="t">전체 보기 · 구매 문의</div>
    <div class="m">{C.EMAIL}</div>
  </div>
  <div class="foot">『{C.TITLE}』 · 호차차 지음 · 종목 추천·수익 보장 아님(투자 교육·실전 기록)</div>
</div></body></html>"""

def build():
    cta_bytes=io.BytesIO(); HTML(string=cta_html(), base_url=str(ROOT)).write_pdf(cta_bytes)
    cta=PdfReader(cta_bytes)
    src=PdfReader(str(SRC))
    w=PdfWriter()
    for i in range(LAST): w.add_page(src.pages[i])
    w.add_page(cta.pages[0])
    w.add_metadata({"/Title":f"{C.TITLE} (미리보기)","/Author":C.AUTHOR,
                    "/Subject":"미리보기 — 표지·프롤로그·1장","/Keywords":"AI 투자, 주식투자, 미리보기"})
    with open(OUT,"wb") as f: w.write(f)
    print("[ok] 샘플 PDF →", OUT, f"({LAST+1}쪽)")

if __name__=="__main__": build()
