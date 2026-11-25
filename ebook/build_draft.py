# -*- coding: utf-8 -*-
"""집필 중 원고 검토용 PDF(정식 조판 전). source/bookN.md → pandoc HTML → WeasyPrint.
사용: python3 build_draft.py 4   → publish/book4/<파일명>_초고.pdf
책 정보는 아래 BOOKS에 둔다(정식 조판 때는 contentN.py로 옮긴다)."""
import pathlib, re, subprocess, sys
from weasyprint import HTML

ROOT = pathlib.Path(__file__).resolve().parent
BOOKS = {
    "4": dict(title="호재일까,<br><em>함정</em>일까", plain="호재일까, 함정일까",
              sub="AI와 함께 읽는 DART 공시, 뉴스보다 먼저 온 한 줄", file="호재일까함정일까",
              colors={"--blue": "#1D1D1F", "--red": "#8A6D00", "--tint": "#FFF6C7"},   # 먹색 + 형광 노랑(글자용은 어두운 황토)
              start="# 이 책을 읽기 전에"),
    "5": dict(title="<em>매수</em> 의견만<br>있는 나라", plain="매수 의견만 있는 나라",
              sub="AI와 함께 읽는 증권사 리포트, 목표주가 뒤에 숨은 가정들", file="매수의견만있는나라",
              colors={"--blue": "#2B3440", "--red": "#C8372D", "--tint": "#EEF1F4"},   # 회청색 + 상승 빨강 한 점(가안)
              start="# 이 책을 읽기 전에"),
}

def build(n, version="v0.1"):
    b = BOOKS[n]
    md = (ROOT / "source" / f"book{n}.md").read_text(encoding="utf-8")
    md = md[md.index(b["start"]):]
    html = subprocess.run(["pandoc", "-f", "markdown", "-t", "html5"], input=md,
                          capture_output=True, text=True, check=True).stdout
    html = re.sub(r'(<h3[^>]*>아이에게 이렇게 설명해 보세요</h3>\s*)(<p>.*?</p>)', r'\1<div class="kid">\2</div>', html, flags=re.S)
    html = re.sub(r'(<h3[^>]*>한 줄 정리</h3>\s*)(<p>.*?</p>)', r'\1<div class="oneline">\2</div>', html, flags=re.S)
    import build_preview                                   # 한글 어절 단위 줄바꿈(WeasyPrint keep-all 무시 우회)
    html = build_preview.keep_words(html)
    css_vars = ";".join(f"{k}:{v}" for k, v in b["colors"].items())
    title = (f'<div class="titlepage"><div class="t">{b["title"]}</div><div class="s">{b["sub"]}<br>호차차 지음 · 유페이퍼</div>'
             f'<div class="v">DRAFT {version}</div></div>')
    doc = (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><link rel="stylesheet" href="assets/draft.css"><style>.kw{{white-space:nowrap}}</style>'
           f'<style>:root{{{css_vars}}}body{{string-set:booktitle "{b["plain"]}"}}'
           f'blockquote:before{{color:#1D1D1F}}h3:before{{color:#C9A400}}</style></head><body>{title}{html}</body></html>')
    out_dir = ROOT / "publish" / f"book{n}"; out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f'{b["file"]}_초고.pdf'
    HTML(string=doc, base_url=str(ROOT)).write_pdf(out)
    return out

if __name__ == "__main__":
    print(build(sys.argv[1] if len(sys.argv) > 1 else "4", *(sys.argv[2:3])))
