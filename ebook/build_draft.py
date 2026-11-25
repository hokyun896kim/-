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
              colors={"--blue": "#0D1117", "--red": "#FF4B3E", "--tint": "#11161D"},   # 터미널 검푸른색 + 신호 빨강(표지와 같은 값)
              start="# 이 책을 읽기 전에", cover="build/img/book5_cover.png",
              # 미래형 = 트레이딩 터미널: 본문은 흰 종이 그대로(읽기), 제목 띠·표·AI 질문 창에만 화면 언어. 글로우·그라데이션 없음
              css="""
body{font-family:"Noto Sans CJK KR";font-size:10pt;line-height:1.9;color:#1A1F26}
@page{@top-center{font-family:"JetBrains Mono","Noto Sans CJK KR";letter-spacing:.12em;color:#8A93A0}
      @bottom-center{font-family:"JetBrains Mono";color:#8A93A0}}
h1{background:#0D1117;color:#EEF1F5;border:0;border-left:6px solid #FF4B3E;padding:5mm 5mm 5mm 6mm;font-size:16pt;margin:0 0 6mm}
h2{font-family:"Noto Sans CJK KR";font-weight:800;color:#0D1117}
h3{color:#0D1117}h3:before{content:"▍";color:#FF4B3E;font-size:11pt}
table{font-family:"JetBrains Mono","Noto Sans CJK KR";font-size:8.4pt;border-top:2px solid #0D1117}
th{background:#0D1117;color:#EEF1F5;letter-spacing:.02em}
td{border-bottom:1px solid #DDE2E8}tr:nth-child(even) td{background:#F4F6F9}
blockquote{background:#11161D;color:#E6EAF0;border:0;border-top:3px solid #FF4B3E;border-radius:0;
  font-family:"JetBrains Mono","Noto Sans CJK KR";font-size:8.8pt;line-height:1.75;padding:3.5mm 4.5mm}
blockquote:before{content:"AI  ›  PROMPT";color:#FF4B3E;font-family:"JetBrains Mono";letter-spacing:.18em;font-size:7pt}
strong{color:#0D1117;background:linear-gradient(transparent 62%,#FFD9D5 62%)}
th strong,td strong,blockquote strong{background:none;color:inherit}
.oneline{border:0;border-left:4px solid #FF4B3E;background:#F4F6F9;padding:3.5mm 4.5mm;color:#0D1117}
.oneline:before{content:"SUMMARY";display:block;font-family:"JetBrains Mono";font-size:7pt;letter-spacing:.18em;color:#FF4B3E;margin-bottom:1.5mm}
.coverimg{page:cover;page-break-after:always;margin:0}
@page cover{margin:0;@top-center{content:none}@bottom-center{content:none}}
.coverimg img{width:152mm;height:225mm;display:block}
"""),
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
    cover = f'<div class="coverimg"><img src="{b["cover"]}"></div>' if b.get("cover") and (ROOT / b["cover"]).exists() else ""
    title = cover + (f'<div class="titlepage"><div class="t">{b["title"]}</div><div class="s">{b["sub"]}<br>호차차 지음 · 유페이퍼</div>'
             f'<div class="v">DRAFT {version}</div></div>')
    doc = (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><link rel="stylesheet" href="assets/draft.css"><style>.kw{{white-space:nowrap}}</style>'
           f'<style>:root{{{css_vars}}}body{{string-set:booktitle "{b["plain"]}"}}'
           f'blockquote:before{{color:#1D1D1F}}h3:before{{color:#C9A400}}</style><style>{b.get("css","")}</style></head><body>{title}{html}</body></html>')
    out_dir = ROOT / "publish" / f"book{n}"; out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f'{b["file"]}_초고.pdf'
    HTML(string=doc, base_url=str(ROOT)).write_pdf(out)
    return out

if __name__ == "__main__":
    print(build(sys.argv[1] if len(sys.argv) > 1 else "4", *(sys.argv[2:3])))
