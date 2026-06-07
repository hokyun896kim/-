# -*- coding: utf-8 -*-
"""
개념 도식(설명 삽화) ― 본문 중간에 들어가 이해를 돕는 '그려진 그림'.
장마다 내용에 맞는 서로 다른 도식. SVG→PNG(한글 라벨 포함). 산출: build/img/fig_<n>.png
"""
import math, pathlib, cairosvg

IMG=(pathlib.Path(__file__).resolve().parent/"build"/"img"); IMG.mkdir(parents=True,exist_ok=True)
NAVY="#163B4E"; NAVY2="#21566E"; ACCENT="#C0894B"; ACCENTD="#9C6B33"
INK="#2B2724"; MUT="#6E6A63"; CREAM="#F7F2E8"; LINE="#E1D9C9"
GOOD="#2F6F5E"; GOODBG="#EAF1ED"; BAD="#A6433B"; BADBG="#F7EEE8"; FONT="Noto Sans CJK KR"
W=900

def _png(name, body, h, scale=2.3):
    svg=(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}">'
         f'<rect x="1" y="1" width="{W-2}" height="{h-2}" rx="14" fill="{CREAM}" stroke="{LINE}" stroke-width="1.5"/>'
         f'{body}</svg>')
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(IMG/f"{name}.png"),
                     output_width=int(W*scale), output_height=int(h*scale))

def T(x,y,s,size=15,col=INK,w=None,anchor="middle"):
    wt=f' font-weight="{w}"' if w else ''
    return f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}"{wt} fill="{col}" text-anchor="{anchor}">{s}</text>'
def title(s): return T(W/2,44,s,22,NAVY,700)
def cap(y,s): return T(W/2,y,s,14,INK)

def wrap(s,n):
    out=[]; cur=""
    for w in s.split():
        if len(cur)+len(w)+1<=n: cur=(cur+" "+w).strip()
        else: out.append(cur); cur=w
    if cur: out.append(cur)
    return out or [s]

# ---------- 개별 도식 ----------
def fig_1():  # 감정의 진자
    px,py=450,72; H=360
    b=[title("감정의 진자"),
       f'<path d="M250 300 A220 220 0 0 1 650 300" fill="none" stroke="{LINE}" stroke-width="2" stroke-dasharray="5 6"/>',
       f'<line x1="{px}" y1="{py}" x2="255" y2="293" stroke="{BAD}" stroke-width="2" stroke-dasharray="4 6" opacity="0.55"/>',
       f'<line x1="{px}" y1="{py}" x2="645" y2="293" stroke="{ACCENTD}" stroke-width="2" stroke-dasharray="4 6" opacity="0.55"/>',
       f'<line x1="{px}" y1="{py}" x2="{px}" y2="300" stroke="{NAVY}" stroke-width="4"/>',
       f'<circle cx="{px}" cy="{py}" r="6" fill="{NAVY}"/><circle cx="{px}" cy="305" r="34" fill="{NAVY}"/>',
       T(px,312,"나",20,"#fff",700),
       f'<circle cx="200" cy="250" r="40" fill="{BADBG}" stroke="{BAD}" stroke-width="1.5"/>',
       T(200,245,"공포",19,BAD,700), T(200,268,"못 산다",12,MUT),
       f'<circle cx="700" cy="250" r="40" fill="#F6EEDD" stroke="{ACCENTD}" stroke-width="1.5"/>',
       T(700,245,"욕심",19,ACCENTD,700), T(700,268,"못 판다",12,MUT),
       cap(348,"기준이 없으면, 시장이 아니라 내 감정에 휘둘린다.")]
    _png("fig_1","".join(b),H)

def two_path(name,ttl,llabel,lpts,rlabel,rpts,note):  # 갈림길(하락 vs 상승 경로)
    H=360
    b=[title(ttl),
       f'<line x1="60" y1="300" x2="840" y2="300" stroke="{MUT}" stroke-width="1.5"/>',
       f'<circle cx="120" cy="180" r="6" fill="{NAVY}"/>', T(120,150,"같은 출발",12,MUT),
       f'<polyline points="{lpts}" fill="none" stroke="{BAD}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>',
       f'<polyline points="{rpts}" fill="none" stroke="{GOOD}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>',
       T(330,290,llabel,15,BAD,700), T(640,110,rlabel,15,GOOD,700),
       cap(348,note)]
    _png(name,"".join(b),H)

def cycle(name,ttl,nodes,note):  # 순환(악순환/선순환)
    H=380; cx,cy,r=450,205,118
    b=[title(ttl)]
    k=len(nodes)
    pts=[]
    for i,nd in enumerate(nodes):
        a=-math.pi/2+2*math.pi*i/k
        x=cx+r*math.cos(a); y=cy+r*math.sin(a); pts.append((x,y))
    # 화살표 호
    for i in range(k):
        x1,y1=pts[i]; x2,y2=pts[(i+1)%k]
        b.append(f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" stroke="{ACCENT}" stroke-width="2" opacity="0.7"/>')
    for i,(x,y) in enumerate(pts):
        b.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="44" fill="#fff" stroke="{NAVY}" stroke-width="2"/>')
        lines=wrap(nodes[i],7)
        for j,ln in enumerate(lines):
            b.append(T(x,y-2+(j-(len(lines)-1)/2)*16,ln,12.5,NAVY,700))
    b.append(cap(366,note))
    _png(name,"".join(b),H)

def panel2(name,ttl,lt,litems,rt,ritems,note,mid="→"):  # 두 패널 대비
    rows=max(len(litems),len(ritems)); H=140+rows*40+30
    cw=360; lx=40; rx=W-40-cw; topy=70
    b=[title(ttl)]
    for x,head,items,col,bg,mark in [(lx,lt,litems,BAD,BADBG,"✕"),(rx,rt,ritems,GOOD,GOODBG,"✓")]:
        b.append(f'<rect x="{x}" y="{topy}" width="{cw}" height="{rows*40+44}" rx="12" fill="{bg}" stroke="{col}" stroke-width="1.5"/>')
        b.append(T(x+cw/2,topy+28,head,16,col,700))
        for i,it in enumerate(items):
            yy=topy+58+i*40
            b.append(T(x+22,yy,mark,14,col,700,anchor="start"))
            b.append(T(x+44,yy,it,13.5,INK,anchor="start"))
    cyc=topy+(rows*40+44)/2
    b.append(f'<circle cx="{W/2}" cy="{cyc:.0f}" r="22" fill="#fff" stroke="{ACCENT}" stroke-width="2"/>')
    b.append(T(W/2,cyc+8,mid,22,ACCENTD,800))
    b.append(cap(H-16,note))
    _png(name,"".join(b),H)

def fan(name,ttl,center,leaves,note,ccolor=NAVY):  # 중심 → 부채꼴 갈래
    H=360; cx,cy=170,190
    b=[title(ttl),
       f'<rect x="60" y="{cy-34}" width="170" height="68" rx="12" fill="{ccolor}"/>',
       T(145,cy+7,center,18,"#fff",700)]
    n=len(leaves); top=95; gap=(330-top)/(n-1) if n>1 else 0
    for i,lf in enumerate(leaves):
        ly=top+gap*i
        b.append(f'<line x1="230" y1="{cy}" x2="430" y2="{ly:.0f}" stroke="{ACCENT}" stroke-width="2"/>')
        b.append(f'<rect x="430" y="{ly-22:.0f}" width="410" height="44" rx="10" fill="#fff" stroke="{LINE}" stroke-width="1.5"/>')
        b.append(T(450,ly+6,lf,14,NAVY,700,anchor="start"))
    b.append(cap(H-12,note))
    _png(name,"".join(b),H)

def hourglass(name,ttl,top,bottom,note):  # 모래시계
    H=370; cx=450
    b=[title(ttl),
       f'<path d="M360 90 H540 L470 200 H430 Z" fill="{ACCENT}" opacity="0.85"/>',
       f'<path d="M430 200 H470 L540 310 H360 Z" fill="{NAVY}" opacity="0.85"/>',
       f'<line x1="350" y1="90" x2="550" y2="90" stroke="{NAVY}" stroke-width="4" stroke-linecap="round"/>',
       f'<line x1="350" y1="310" x2="550" y2="310" stroke="{NAVY}" stroke-width="4" stroke-linecap="round"/>',
       T(cx,150,top,14,"#fff",700), T(cx,285,bottom,13,"#fff",700),
       cap(H-14,note)]
    _png(name,"".join(b),H)

def donut(name,ttl,slices,note):  # 도넛(쏠림)
    H=370; cx,cy,r=300,200,110; inner=58
    b=[title(ttl)]; a0=-90; tot=sum(s[1] for s in slices)
    cols=[ACCENT,NAVY,NAVY2,"#7d9aa6",LINE]
    for i,(lab,val) in enumerate(slices):
        a1=a0+360*val/tot
        x0=cx+r*math.cos(math.radians(a0)); y0=cy+r*math.sin(math.radians(a0))
        x1=cx+r*math.cos(math.radians(a1)); y1=cy+r*math.sin(math.radians(a1))
        large=1 if a1-a0>180 else 0
        b.append(f'<path d="M{cx} {cy} L{x0:.1f} {y0:.1f} A{r} {r} 0 {large} 1 {x1:.1f} {y1:.1f} Z" fill="{cols[i%len(cols)]}"/>')
        a0=a1
    b.append(f'<circle cx="{cx}" cy="{cy}" r="{inner}" fill="{CREAM}"/>')
    # 범례
    ly=110
    for i,(lab,val) in enumerate(slices):
        b.append(f'<rect x="500" y="{ly-12}" width="16" height="16" rx="3" fill="{cols[i%len(cols)]}"/>')
        b.append(T(525,ly+2,f"{lab}",14,INK,anchor="start"))
        ly+=34
    b.append(cap(H-14,note))
    _png(name,"".join(b),H)

def arrows5(name,ttl,items,note):  # 급등 5유형 화살표
    H=340; b=[title(ttl)]
    shapes={"뉴스형":"110,250 140,120 170,250","수급형":"100,250 180,140",
            "섹터형":"100,250 140,180 180,160","실적형":"100,250 160,150 200,130",
            "과열형":"100,250 150,230 170,90"}
    x=20; cw=172
    for nm,desc in items:
        cxr=x+cw/2
        pts=shapes.get(nm,"100,250 180,140")
        # 위치 이동
        seg=[]
        for p in pts.split():
            a,bb=p.split(","); seg.append(f"{float(a)-100+x+30:.0f},{bb}")
        b.append(f'<polyline points="{" ".join(seg)}" fill="none" stroke="{ACCENT}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>')
        b.append(T(cxr,290,nm,14,NAVY,700))
        x+=cw
    b.append(cap(H-14,note))
    _png(name,"".join(b),H)

def gauge(name,ttl,segs,note):  # 반원 게이지(태도)
    H=340; cx,cy,r=450,260,180
    b=[title(ttl)]; n=len(segs)
    cols=["#7a3a33",ACCENT,NAVY2,NAVY,"#33564f"]
    for i,seg in enumerate(segs):
        a0=180-180*i/n; a1=180-180*(i+1)/n
        x0=cx+r*math.cos(math.radians(a0)); y0=cy-r*math.sin(math.radians(a0))
        x1=cx+r*math.cos(math.radians(a1)); y1=cy-r*math.sin(math.radians(a1))
        xi0=cx+110*math.cos(math.radians(a0)); yi0=cy-110*math.sin(math.radians(a0))
        xi1=cx+110*math.cos(math.radians(a1)); yi1=cy-110*math.sin(math.radians(a1))
        b.append(f'<path d="M{x0:.1f} {y0:.1f} A{r} {r} 0 0 1 {x1:.1f} {y1:.1f} L{xi1:.1f} {yi1:.1f} A110 110 0 0 0 {xi0:.1f} {yi0:.1f} Z" fill="{cols[i%5]}"/>')
        am=math.radians((a0+a1)/2); lx=cx+150*math.cos(am); ly=cy-150*math.sin(am)
        b.append(T(lx,ly+4,seg,12.5,"#fff",700))
    b.append(cap(H-14,note))
    _png(name,"".join(b),H)

def steps(name,ttl,items,note):  # 가로 단계
    H=300; b=[title(ttl)]; n=len(items)
    bw=150; gap=(W-80-bw*n)/(n-1) if n>1 else 0; x=40; y=150
    for i,(t,d) in enumerate(items):
        b.append(f'<rect x="{x:.0f}" y="{y-50}" width="{bw}" height="100" rx="12" fill="#fff" stroke="{LINE}" stroke-width="1.5"/>')
        b.append(f'<circle cx="{x+24:.0f}" cy="{y-26}" r="14" fill="{ACCENT}"/>')
        b.append(T(x+24,y-21,str(i+1),13,"#fff",700))
        for j,ln in enumerate(wrap(t,8)):
            b.append(T(x+bw/2,y+2+j*18,ln,13,NAVY,700))
        if i<n-1:
            ax=x+bw+gap/2
            b.append(f'<path d="M{x+bw+6:.0f} {y} H{x+bw+gap-6:.0f}" stroke="{ACCENT}" stroke-width="2"/>')
            b.append(f'<path d="M{x+bw+gap-6:.0f} {y} l-9 -5 0 10 z" fill="{ACCENT}"/>')
        x+=bw+gap
    b.append(cap(H-14,note))
    _png(name,"".join(b),H)

def timeline(name,ttl,points,note):  # 타임라인
    H=270; b=[title(ttl)]; y=150
    b.append(f'<line x1="80" y1="{y}" x2="820" y2="{y}" stroke="{NAVY}" stroke-width="3"/>')
    b.append(f'<path d="M820 {y} l-12 -6 0 12 z" fill="{NAVY}"/>')
    n=len(points); gap=(740)/(n-1)
    for i,(t,d) in enumerate(points):
        x=80+gap*i
        b.append(f'<circle cx="{x:.0f}" cy="{y}" r="10" fill="{ACCENT}"/>')
        b.append(T(x,y-26,t,15,NAVY,700))
        for j,ln in enumerate(wrap(d,12)):
            b.append(T(x,y+34+j*17,ln,12,MUT))
    b.append(cap(H-12,note))
    _png(name,"".join(b),H)

def fig_5():  # 좋은 기업 ≠ 좋은 주식
    H=360
    def chart(x,ttl,sub,line,dot=None,color=NAVY):
        g=[T(x+130,40,ttl,17,NAVY,700),T(x+130,60,sub,12,MUT),
           f'<line x1="{x+20}" y1="90" x2="{x+20}" y2="270" stroke="{MUT}" stroke-width="2"/>',
           f'<line x1="{x+20}" y1="270" x2="{x+250}" y2="270" stroke="{MUT}" stroke-width="2"/>',
           f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>']
        if dot: g+=[f'<circle cx="{dot[0]}" cy="{dot[1]}" r="7" fill="{ACCENT}"/>',T(dot[0],dot[1]-14,"지금",12,ACCENTD,700)]
        return "".join(g)
    b=[title("좋은 기업 ≠ 좋은 주식") if False else "",
       chart(30,"좋은 기업 (사업 가치)","실적이 꾸준히 우상향","50,260 110,235 170,205 230,175 270,150",color=GOOD),
       chart(470,"좋은 주식? (가격)","이미 기대가 선반영됨","490,255 540,250 580,150 620,120 700,128 740,132",dot=(620,120),color=BAD),
       f'<circle cx="{W/2}" cy="180" r="26" fill="#fff" stroke="{ACCENT}" stroke-width="2"/>',T(W/2,190,"≠",24,ACCENTD,800),
       cap(342,"좋은 기업이라도, 기대가 이미 가격에 반영됐다면 좋은 주식이 아니다.")]
    _png("fig_5","".join(b),H)

def fig_6():  # 시장 → 섹터 → 종목
    H=360; rows=[("시장","위험선호인가, 위험회피인가 — 가장 큰 방향",120,820,NAVY),
                 ("섹터","돈이 지금 어느 업종으로 이동하는가",210,730,NAVY2),
                 ("종목","그 흐름 안에서 비로소 고른다",320,620,ACCENTD)]
    b=[title("돈은 위에서 아래로 흐른다")]; y=70
    for i,(t,d,x1,x2,c) in enumerate(rows):
        yy=y+i*88
        b.append(f'<path d="M{x1} {yy} H{x2} L{x2-55} {yy+66} H{x1+55} Z" fill="{c}" opacity="{0.92-i*0.07}"/>')
        b.append(T(W/2,yy+30,t,20,"#fff",800)); b.append(T(W/2,yy+52,d,12.5,"#EAF0F2"))
        if i<2: b.append(f'<path d="M{W/2} {yy+70} l-9 -2 9 14 9 -14 z" fill="{ACCENT}"/>')
    _png("fig_6","".join(b),H)

# ---------- 빌드 ----------
def build():
    fig_1(); fig_5(); fig_6()
    two_path("fig_2","같은 7천만 원, 갈리는 결과","기준 없이","120,180 220,230 320,210 430,275 540,250 650,295",
             "기준 있게","120,180 240,160 360,150 480,120 600,108 720,80","같은 종잣돈도, 기준이 있느냐에 따라 다른 계좌가 된다.")
    cycle("fig_3","정답을 구하면 빠지는 악순환",["불안","“뭐 살까?”","정답·허락","잠깐 안심"],
          "종목을 물을수록 판단이 아니라 안심만 반복해서 사게 된다.")
    panel2("fig_4","질문이 판단의 순서를 만든다","종목 질문",["“이거 살까요?”","매수·매도 결론","그때뿐인 안심"],
           "시스템 질문",["“무엇을 확인하지?”","확인 순서·조건","반복 가능한 기준"],
           "‘무엇을 살까’ 대신 ‘무엇을 확인할까’로 물으면 순서가 생긴다.")
    panel2("fig_7","정답지 vs 회의실","정답지로 쓸 때",["하나의 답","결정을 떠넘김","틀리면 AI 탓"],
           "회의실로 쓸 때",["여러 관점","근거로 내가 결정","기준을 재점검"],
           "AI에게 결정을 맡기면 점쟁이, 관점을 물으면 투자위원회가 된다.")
    gauge("fig_8","장전, 오늘의 태도를 먼저 정한다",["공격","정찰","유지","감량","현금대기"],
          "종목을 찾기 전에 오늘이 어떤 날인지부터 정한다.")
    cycle("fig_9","기록이 다음 판단을 바꾼다",["매매","기록(이유)","복기","더 나은 판단"],
          "계좌는 결과를, 기록은 이유를 남긴다. 그 이유가 다음을 바꾼다.")
    fan("fig_10","현금은 ‘선택권’이다","현금",["하락장에서 계좌를 지키는 방어","좋은 기회가 왔을 때 살 권리","더 나은 종목으로 갈아탈 재원","흔들릴 때 버티게 하는 심리 안정"],
        "현금은 노는 돈이 아니라, 다음 판단을 살 수 있는 선택권이다.")
    hourglass("fig_11","익절 = 시간을 사는 일","상승분 잠금","다음 판단을 위한 시간·현금",
              "익절은 상승을 포기하는 게 아니라, 다음 판단을 위한 시간을 사는 일.")
    donut("fig_12","포트폴리오 = 욕망의 지도",[("한 섹터 쏠림",46),("성장주",24),("방어주",16),("현금",14)],
          "포트폴리오는 내가 어떤 미래에 베팅하는지 보여주는 지도다.")
    arrows5("fig_13","급등에도 결이 있다",[("뉴스형",""),("수급형",""),("섹터형",""),("실적형",""),("과열형","")],
            "같은 급등도 유형을 나누면, 추격할지 기다릴지 보낼지가 보인다.")
    fan("fig_14","이 하락은 어떤 하락인가?","하락",["단순 조정 — 보유 논리 유지","섹터 약화 — 비중 점검","종목 고유 문제 — 근거 재검토","시장 위험회피 — 현금·방어"],
        "가격이 빠졌다는 사실보다, 하락의 ‘성격’을 먼저 나눈다.",ccolor=BAD)
    panel2("fig_15","리포트를 읽는 두 렌즈","지형도용",["산업·판도 이해","구조·경쟁력·전망","“판이 어떻게 바뀌나?”"],
           "트리거용",["단기 매매 신호","목표가·서프라이즈·수급","“지금 무엇이 달라졌나?”"],
           "같은 리포트도 넓게(지형도)와 좁게(트리거) 나눠 읽는다.",mid="↔")
    fan("fig_16","닫힌 질문은 막다른 길","“살까요?”",["정답을 떠넘긴다","듣고 싶은 답만 고른다","틀리면 AI 탓","판단이 아니라 안심을 산다"],
        "결론을 재촉하는 질문은, 결국 안심만 사고 판단을 남기지 못한다.",ccolor=BAD)
    fan("fig_17","좋은 질문은 판단을 펼친다","“무엇을 확인?”",["실적 — 지속되는가","가격 — 기대가 반영됐나","리스크 — 무엇이 틀리면 아웃","반증 — 어떤 신호면 손절"],
        "좋은 질문 하나가 실적·가격·리스크·반증으로 판단을 펼쳐준다.",ccolor=GOOD)
    steps("fig_18","장전 5분 루틴",[("오늘의 태도",""),("밤사이 글로벌",""),("유리한 쪽",""),("볼 섹터 3개",""),("계좌 점검","")],
          "종목을 찾기 전, 5분이면 오늘의 작전 회의가 끝난다.")
    timeline("fig_19","하루를 기록으로 잇는다",[("오늘","무슨 장이었나"),("기록","판단의 질·이유"),("내일","확인할 체크포인트 3개")],
             "계좌만 보지 않고 하루를 기록하면, 오늘이 내일로 이어진다.")
    print("[ok] concept figures: fig_1 ~ fig_19")

if __name__=="__main__":
    build()
