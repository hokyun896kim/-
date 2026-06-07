#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 미리보기 생성기 ― content.parse() 요소를 HTML로 렌더 후 WeasyPrint로 PDF.
Word(book.docx)와 동일한 콘텐츠/디자인을 시각 확인하기 위한 용도.
산출물: ebook/build/preview.pdf
"""
import html, pathlib
from weasyprint import HTML
import content as C

ROOT=pathlib.Path(__file__).resolve().parent
ASSETS=ROOT/"assets"; BUILD=ROOT/"build"; BUILD.mkdir(exist_ok=True)
TOC=[]

def esc(s): return html.escape(s)

def render():
    parts=[]
    for el in C.parse():
        t=el[0]
        if t=='cover':
            parts.append(f'''<section class="cover"><div class="inner">
              <div class="eyebrow">AI · INVESTING · SYSTEM</div>
              <h1>나는 AI에게<br>종목을 묻지 않았다</h1><div class="rule"></div>
              <div class="sub">{esc(C.SUBTITLE)}</div>
              <div class="key">“{esc(C.KEYLINE)}”</div>
              <div class="foot">{esc(C.PROJECT)}</div></div></section>''')
        elif t=='disclaimer':
            items="".join(f"<p>{esc(d)}</p>" for d in el[1])
            parts.append(f'<section class="frontmatter"><h2 class="plain">일러두기</h2>'
                         f'<div class="disclaimer"><span class="tag">DISCLAIMER</span>{items}</div></section>')
        elif t=='toc':
            parts.append("<!--TOC-->")
        elif t=='part':
            anchor=f"part{el[1]}"; TOC.append(("part",anchor,f"{el[1]}부. {el[2]}"))
            parts.append(f'<h1 class="part" id="{anchor}"><span class="pno">{esc(el[1])}부</span>{esc(el[2])}</h1>')
        elif t=='h1big':
            kind=el[1]; anchor=f"{kind}{len(TOC)}"
            TOC.append((kind,anchor,el[2]))
            parts.append(f'<h2 class="chapter" id="{anchor}">{esc(el[2])}</h2>')
        elif t=='chapter':
            anchor=f"ch{el[1]}"; TOC.append(("chapter",anchor,f"{el[1]}장. {el[2]}"))
            parts.append(f'<h2 class="chapter" id="{anchor}">{el[1]}장. {esc(el[2])}</h2>')
        elif t=='keysentence':
            parts.append(f'<div class="keybox"><span class="klabel">이 장의 핵심</span>'
                         f'<p>{esc(el[1])}</p></div>')
        elif t=='callout':
            parts.append(f'<div class="callout"><p class="ctitle">{esc(el[1])}</p><p>{esc(el[2])}</p></div>')
        elif t=='compare':
            headers,rows,good_right=el[1],el[2],el[3]
            clsA,clsB=("col-bad","col-good") if good_right else ("col-good","col-bad")
            body="".join(f'<tr><th>{esc(a)}</th><td class="{clsA}">{esc(b)}</td><td class="{clsB}">{esc(c)}</td></tr>'
                         for a,b,c in rows)
            parts.append(f'<table class="compare"><thead><tr><th></th><th>{esc(headers[1])}</th>'
                         f'<th>{esc(headers[2])}</th></tr></thead><tbody>{body}</tbody></table>')
        elif t=='cards':
            body="".join(f'<div class="card"><span class="cidx">{i}</span><h4>{esc(x[0])}</h4>'
                         f'<p>{esc(x[1])}</p></div>' for i,x in enumerate(el[1],1))
            parts.append(f'<div class="cardgrid">{body}</div>')
        elif t=='modebar':
            body="".join(f'<div class="mode"><b>{esc(n)}</b>{esc(d)}</div>' for n,d in el[1])
            parts.append(f'<div class="modebar">{body}</div>')
        elif t=='flow':
            body="".join(f'<div class="step"><div class="dot">{i}</div><div class="body">'
                         f'<h4>{esc(x[0])}</h4><p>{esc(x[1])}</p></div></div>' for i,x in enumerate(el[1],1))
            parts.append(f'<div class="flow">{body}</div>')
        elif t=='dodont':
            label,items,kind=el[1],el[2],el[3]; mark="✕" if kind=="dont" else "✓"
            lis="".join(f'<li><span class="qnum">{mark}</span>{esc(a)} — <span class="fillline">{esc(b)}</span></li>'
                        for a,b in items)
            parts.append(f'<div class="{kind}"><span class="lbl">{esc(label)}</span>'
                         f'<ul class="checklist" style="margin:0">{lis}</ul></div>')
        elif t=='h3': parts.append(f'<h3>{esc(el[1])}</h3>')
        elif t=='para': parts.append(f'<p>{esc(el[1])}</p>')
        elif t=='bullets':
            parts.append('<ul class="bullets">'+''.join(f'<li>{esc(x)}</li>' for x in el[1])+'</ul>')
        elif t=='numlist':
            parts.append('<ol class="numlist">'+''.join(f'<li>{esc(x)}</li>' for x in el[1])+'</ol>')
        elif t=='cat':
            parts.append(f'<p class="apx-cat"><span>{esc(el[1])}</span>{esc(el[2])}</p>')
        elif t=='q':
            qmode,num,text=el[1],el[2],el[3]
            badge=f'<span class="qnum">Q{num}</span>' if qmode else f'<span class="qnum">{num}.</span>'
            parts.append(f'<p class="apx-q">{badge}{esc(text)}</p>')
        elif t=='prompt':
            parts.append(f'<div class="prompt"><span class="ptag">붙여넣을 프롬프트</span>{esc(el[1])}</div>')
        elif t=='fill':
            parts.append(f'<p class="fillline">{esc(el[1])}<span class="fillrule" style="display:block"></span></p>')
    body="\n".join(parts)

    # 목차 생성
    rows=[]
    for kind,anchor,label in TOC:
        if kind=="part":
            num,_,rest=label.partition(". ")
            rows.append(f'<div class="tpart"><span class="pno">{esc(num)}</span>{esc(rest)}</div>')
        else:
            rows.append(f'<li><a href="#{anchor}"><span class="t">{esc(label)}</span><span class="dots"></span></a></li>')
    toc=f'<section class="toc"><h2 class="plain">차례</h2><ol>{"".join(rows)}</ol></section>'
    body=body.replace("<!--TOC-->", toc)

    css=(ASSETS/"preview.css").read_text(encoding="utf-8")
    doc=f'<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><style>{css}</style></head><body>{body}</body></html>'
    (BUILD/"preview.html").write_text(doc,encoding="utf-8")
    HTML(string=doc,base_url=str(ROOT)).write_pdf(str(BUILD/"preview.pdf"))
    print("[ok] preview PDF →", BUILD/"preview.pdf")

if __name__=="__main__": render()
