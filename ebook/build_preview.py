#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 미리보기 생성기 ― content.parse() 요소를 HTML로 렌더 후 WeasyPrint로 PDF.
Word(book.docx)와 동일한 콘텐츠/디자인을 시각 확인하기 위한 용도.
산출물: ebook/build/preview.pdf
"""
import html, pathlib, re
from weasyprint import HTML
import content as C

ROOT=pathlib.Path(__file__).resolve().parent
ASSETS=ROOT/"assets"; BUILD=ROOT/"build"; BUILD.mkdir(exist_ok=True)
TOC=[]

def esc(s): return html.escape(s)

def opener_html(icon, eyebrow, title, anchor, subtitle=None):
    img=f'<img class="heroimg" src="build/img/hero_{icon}.png">' if icon else ''
    eb=f'<div class="ceyebrow">{esc(eyebrow)}</div>' if eyebrow else ''
    sub=f'<div class="csub">{esc(subtitle)}</div>' if subtitle else ''
    return (f'<section class="chapopen" id="{anchor}">{img}{eb}'
            f'<h2 class="chaptit">{esc(title)}</h2>{sub}</section>')

def first_sentence_split(text):
    # 따옴표가 끼지 않은 짧고 깔끔한 첫 문장만 도입문으로(없으면 None)
    m=re.match(r'^([^"“”]{6,38}?[.?!])\s*(.*)$', text, re.S)
    if m and len(m.group(1))<=38: return m.group(1), m.group(2)
    return None, text

def render():
    if not (BUILD/"img"/"heart.png").exists():
        import make_assets; make_assets.build()
    parts=[]
    for el in C.parse():
        t=el[0]
        if t=='cover':
            parts.append('<section class="coverpage"></section>')
        elif t=='disclaimer':
            items="".join(f"<p>{esc(d)}</p>" for d in el[1])
            parts.append(f'<section class="frontmatter"><h2 class="plain">일러두기</h2>'
                         f'<div class="disclaimer"><span class="tag">DISCLAIMER</span>{items}</div>'
                         f'<p class="readkey">이 책의 핵심은 종목명이 아니라 ‘질문의 구조’입니다.</p>'
                         f'<p class="readguide">이 책은 순서대로 읽어도 좋지만, 6부와 부록은 필요할 때 다시 꺼내보는 '
                         f'실전 노트처럼 활용하셔도 좋습니다.</p></section>')
        elif t=='toc':
            parts.append("<!--TOC-->")
        elif t=='part':
            anchor=f"part{el[1]}"; TOC.append(("part",anchor,f"{el[1]}부. {el[2]}"))
            icon=el[3] if len(el)>3 else ''; intro=el[4] if len(el)>4 else ''
            img=f'<img class="partimg" src="build/img/{icon}.png">' if icon else ''
            it=f'<p class="pintro">{esc(intro)}</p>' if intro else ''
            parts.append(f'<section class="partpage" id="{anchor}">{img}'
                         f'<div class="pno">{esc(el[1])}부</div><h1 class="part">{esc(el[2])}</h1>{it}</section>')
        elif t=='h1big':
            kind=el[1]; anchor=f"{kind}{len(TOC)}"; icon=el[3] if len(el)>3 else ''
            if kind=='prologue':
                TOC.append((kind,anchor,"프롤로그"))
                parts.append(opener_html(icon,"","프롤로그",anchor,subtitle=el[2]))
            elif kind=='epilogue':
                TOC.append((kind,anchor,"에필로그"))
                parts.append(opener_html(icon,"","에필로그",anchor,subtitle=el[2]))
            else:
                TOC.append((kind,anchor,el[2]))
                parts.append(opener_html(icon,"APPENDIX",el[2],anchor))
        elif t=='chapter':
            anchor=f"ch{el[1]}"; icon=el[3] if len(el)>3 else ''
            TOC.append(("chapter",anchor,f"{el[1]}장. {el[2]}"))
            parts.append(opener_html(icon, f"CHAPTER {el[1]}", f"{el[1]}장. {el[2]}", anchor))
        elif t=='keysentence':
            parts.append(f'<div class="keybox"><div class="ktext"><span class="klabel">이 장의 핵심</span>'
                         f'<p>{esc(el[1])}</p></div></div>')
        elif t=='ornament':
            parts.append('<div class="ornament"><img src="build/img/ornament.png"></div>')
        elif t=='figure':
            cap=(f'<figcaption><span class="figtag">개념도</span>{esc(el[2])}</figcaption>'
                 if len(el)>2 and el[2] else '')
            parts.append(f'<figure class="cfig"><img src="build/img/{el[1]}.png">{cap}</figure>')
        elif t=='callout':
            parts.append(f'<div class="callout"><p class="ctitle">{esc(el[1])}</p><p>{esc(el[2])}</p></div>')
        elif t=='compare':
            headers,rows,good_right=el[1],el[2],el[3]
            caption=el[4] if len(el)>4 else ''
            clsA,clsB=("col-bad","col-good") if good_right else ("col-good","col-bad")
            body="".join(f'<tr><td class="{clsA}">{esc(b)}</td><td class="{clsB}">{esc(c)}</td></tr>'
                         for a,b,c in rows)
            capt=f'<p class="tcap">{esc(caption)}</p>' if caption else ''
            parts.append(f'<table class="compare"><thead><tr><th>{esc(headers[1])}</th>'
                         f'<th>{esc(headers[2])}</th></tr></thead><tbody>{body}</tbody></table>{capt}')
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
        elif t=='pullquote':
            parts.append(f'<blockquote class="pull"><p>{esc(el[1])}</p></blockquote>')
        elif t=='h3': parts.append(f'<h3>{esc(el[1])}</h3>')
        elif t=='para':
            if len(el)>2 and el[2] and el[1]:   # 장 첫 문단: 짧고 깔끔한 첫 문장만 굵게
                lead,rest=first_sentence_split(el[1])
                if lead:
                    parts.append(f'<p class="leadp"><strong class="lead">{esc(lead)}</strong> {esc(rest)}</p>')
                else:
                    parts.append(f'<p>{esc(el[1])}</p>')
            else:
                parts.append(f'<p>{esc(el[1])}</p>')
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
