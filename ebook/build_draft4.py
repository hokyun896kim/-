# -*- coding: utf-8 -*-
"""4권 초고 확인용 PDF: source/book4.md → pandoc HTML → WeasyPrint. 정식 조판 전 원고 검토용.
산출: publish/book4/사인은내일할게요_초고.pdf"""
import pathlib, re, subprocess
from weasyprint import HTML
import infographic4

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "publish" / "book4"; OUT.mkdir(parents=True, exist_ok=True)

def build(version="v0.2"):
    infographic4.build()                         # 그림의 숫자는 원고와 대조되어야 생성된다
    md = (ROOT / "source" / "book4.md").read_text(encoding="utf-8")
    md = md[md.index("# 이 책을 읽기 전에"):]
    html = subprocess.run(["pandoc", "-f", "markdown", "-t", "html5"], input=md,
                          capture_output=True, text=True, check=True).stdout
    html = re.sub(r'(<h3[^>]*>아이에게 이렇게 설명해 보세요</h3>\s*)(<p>.*?</p>)', r'\1<div class="kid">\2</div>', html, flags=re.S)
    html = re.sub(r'(<h3[^>]*>한 줄 정리</h3>\s*)(<p>.*?</p>)', r'\1<div class="oneline">\2</div>', html, flags=re.S)
    title = ('<div class="titlepage"><div class="t">사인은<br><em>내일</em> 할게요</div>'
             '<div class="s">대출·보험·연금, 서명하기 전에 AI와 숫자로 따져 본 것들<br>호차차 지음 · 유페이퍼</div>'
             f'<div class="v">DRAFT {version}</div></div>')
    doc = (f'<!doctype html><html lang="ko"><head><meta charset="utf-8">'
           f'<link rel="stylesheet" href="assets/draft4.css"></head><body>{title}{html}</body></html>')
    out = OUT / "사인은내일할게요_초고.pdf"
    HTML(string=doc, base_url=str(ROOT)).write_pdf(out)
    return out

if __name__ == "__main__":
    print(build())
