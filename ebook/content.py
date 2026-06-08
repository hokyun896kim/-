# -*- coding: utf-8 -*-
"""
공용 콘텐츠 처리 ― 원고(v1.1)를 '구조화된 요소 목록'으로 변환.
build_docx.py(Word)와 build_preview.py(PDF 미리보기)가 함께 사용한다.

편집 처리:
  · 프롤로그 압축본(PROLOGUE) 사용
  · 한 문장씩 끊긴 문단을 ~300자 단위로 병합
  · '핵심 문장 | …' → keysentence 요소
  · 선별 장에 그래픽(비교표/카드/흐름도/모드바/Do-Dont) 삽입
"""
import re, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
SRC  = ROOT / "source" / "raw_v1.1.md"

TITLE="나는 AI에게 종목을 묻지 않았다"
SUBTITLE="7천만 원 계좌에서 시작된 질문, AI 투자 시스템의 시작"
KEYLINE="나는 AI에게 정답을 묻지 않았다. AI를 내 투자위원회로 만들기 시작했다."
PROJECT="호차차"
AUTHOR="호차차"                     # 필명 (바꾸면 전체 반영)
EMAIL="contact@example.com"        # 문의 이메일 (실제 주소로 교체)
PUBDATE="2026년 6월 초판 1쇄"
AUTHOR_BIO=("개인투자자. AI를 ‘종목 추천기’가 아니라 ‘투자 판단을 점검하는 회의실’로 "
 "쓰기 시작하면서, 장전·장마감 루틴과 섹터·포트폴리오 점검 질문을 만들어 왔다. "
 "이 책은 그 과정을 정리한 실전 기록이다. 여전히 자주 틀리고 급등주 앞에서 흔들리지만, "
 "‘뭘 살까’ 대신 ‘무엇을 확인할까’를 묻는 습관 하나만은 지키려 한다.")

DISCLAIMER=[
 "이 책은 특정 종목의 매수·매도를 권유하기 위한 책이 아닙니다.",
 "저자가 실제 투자 과정에서 AI를 활용해 시장을 해석하고, 투자 판단을 구조화하고, 포트폴리오를 관리하기 시작한 기록입니다.",
 "책에 등장하는 종목과 사례는 판단 프레임을 설명하기 위한 예시이며, 독자의 투자 성향·자산 규모·위험 감내도에 따라 판단은 달라질 수 있습니다.",
 "핵심은 종목명이 아니라 질문법·루틴·기록·복기·비중 조절에 대한 사고방식입니다.",
]

PROLOGUE=[
 '혹시 AI에게 “지금 뭐 사면 좋을까요?”, “이 종목 내일 오를까요?”, “지금 들어가도 늦지 않았나요?” 같은 질문을 해본 적 있으십니까? 저는 해봤습니다. 그것도 아주 많이. 처음 AI를 투자에 활용하려 했을 때, 제가 가장 먼저 떠올린 질문 역시 늘 종목이었습니다. 무엇을 사야 하는지, 언제 팔아야 하는지, 내일 오를지, 지금 사도 되는지.',
 '계좌가 흔들릴 때마다 저는 답을 찾고 싶었습니다. 그런데 돌이켜보면 그건 답이라기보다 허락에 가까웠습니다. “사도 됩니다.”, “괜찮습니다.”, “아직 들고 가도 됩니다.” 그런 말을 들으면 마음이 조금 편해질 것 같았으니까요. 돈이 걸려 있으면 누구나 흔들립니다. 저 역시 주가가 오르면 더 오를 것 같아 팔지 못했고, 빠지면 더 빠질 것 같아 사지 못했습니다. 저는 종목을 분석한다고 믿었지만, 실은 많은 순간 시장이 아니라 제 감정에 반응하고 있었습니다.',
 '처음 종자돈은 7천만 원이었습니다. 누군가에겐 큰돈이고 누군가에겐 작겠지만, 제겐 결코 가볍지 않은 돈이었습니다. 처음에는 단순하게 생각했습니다. 좋은 기업, 실적 좋은 기업, 성장하는 산업의 기업을 찾아 오래 들고 있으면 된다고. 틀린 말은 아니었지만 충분한 말도 아니었습니다. 좋은 기업도 너무 비싸게 사면 고생하고, 좋은 뉴스도 시장이 이미 알고 있었다면 반응은 차갑습니다. 투자는 생각보다 복잡했습니다.',
 '그 복잡함 앞에서 저는 자주 단순한 답을 원했습니다. “살까요, 팔까요, 버틸까요?” AI에게도 처음엔 그렇게 물었고, AI는 제법 그럴듯한 답을 해줬습니다. 그런데 이상하게도 답을 들어도 제 매매는 달라지지 않았습니다. 여전히 급등주를 보면 조급했고, 하락장을 보면 불안했습니다. 그때 알게 됐습니다. 문제는 AI가 아니라 제가 던지는 질문이었습니다. 저는 AI에게 투자 판단을 맡긴 게 아니라, 제 불안을 달래달라고 하고 있었던 겁니다.',
 '그때부터 질문을 바꿨습니다. “이 종목 살까요?” 대신 “이 종목을 사려면 무엇을 확인해야 하나요?”라고. “내일 오를까요?” 대신 “어떤 조건에서 오르고, 어떤 신호가 나오면 틀린 건가요?”라고. “좋은 기업인가요?” 대신 “좋은 건 알겠는데, 지금 좋은 주식인가요?”라고. 질문이 바뀌자 AI의 답도 바뀌었습니다. AI는 더 이상 종목을 찍어주는 도구가 아니라, 제 판단을 기업·가격·섹터·시장·수급·리스크·현금·비중·감정으로 쪼개주는 도구가 되었습니다.',
 '예전엔 머릿속에서 욕심과 공포가 동시에 떠들었습니다. “지금 안 사면 늦어.”, “아니야, 더 빠질 거야.” 시끄러웠습니다. 그런데 AI를 다르게 쓰기 시작하자 그 시끄러운 머릿속이 조금씩 회의실처럼 바뀌었습니다. 욕심이 말하면 리스크를 물었고, 공포가 말하면 보유 논리를 확인했습니다. AI는 제게 정답지를 준 것이 아니라 회의실을 만들어줬습니다.',
 '그 회의실에서 저는 제 판단을 테이블 위에 올리기 시작했습니다. 장 시작 전에는 오늘이 공격할 날인지 지킬 날인지 태도부터 정했고, 장이 끝나면 계좌만 보는 대신 하루를 몇 줄로 기록했습니다. 그 몇 줄이 쌓이자 하루하루의 등락이 흐름으로 보이기 시작했습니다. 급등주는 무조건 따라갈 대상이 아니라 시장의 힌트일 수 있었고, 하락장은 도망칠 공포가 아니라 신호를 나눠봐야 할 구간이었습니다. 현금은 노는 돈이 아니라 다음 판단을 살 선택권이었고, 익절은 상승을 포기하는 일이 아니라 다음 판단을 위한 시간을 사는 일이었습니다.',
 '이 책은 그 변화에 관한 이야기입니다. AI가 종목을 찍어줘 돈을 벌었다는 이야기도, AI가 미래를 맞혔다는 이야기도 아닙니다. 제가 경험한 AI의 진짜 쓸모는 훨씬 현실적인 곳에 있었습니다. AI는 제가 더 좋은 질문을 던지게 했고, 놓친 변수를 보게 했고, 듣고 싶은 말만 찾지 않게 했고, 감정과 판단을 분리하게 했습니다. 그 과정에서 계좌도 달라졌지만, 무엇보다 제가 시장을 대하는 방식이 달라졌습니다.',
 '이 책에 제 모든 시스템을 다 담지는 않았습니다. 솔직히 말하면 일부러 다 꺼내지 않았습니다. 처음부터 모든 도구를 펼쳐놓으면 독자는 다시 도구에 끌려가기 쉽기 때문입니다. 중요한 것은 도구보다 관점이고, 시스템보다 먼저 필요한 것은 질문의 방향입니다. 그래서 이 책은 시작에 집중합니다. 당장 거대한 시스템을 만들 필요는 없습니다. 딱 하나만 바꾸면 됩니다. “뭐 사면 돼?”가 아니라 “지금 내가 무엇을 확인해야 하지?”라고 묻는 것.',
 '저는 AI에게 종목을 묻지 않기로 했습니다. 대신 제 판단을 묻기 시작했습니다. 그리고 그때부터, 투자는 조금씩 다른 일이 되었습니다.',
]
PROLOGUE_KEY="AI에게 종목을 묻는 순간, 저는 정답이 아니라 허락을 찾고 있었습니다."

# 장/부 주제 아이콘 (build/img/*.png)
CH_ICON={1:"heart",2:"seed",3:"chat_q",4:"gear",5:"scale",6:"cycle",7:"table",8:"sunrise",
 9:"notebook",10:"coins",11:"hourglass",12:"compass",13:"surge",14:"umbrella",15:"docmag",
 16:"chat_x",17:"chat_check",18:"clipboard",19:"moon"}
PART_ICON={"1":"part_heart","2":"part_gear","3":"part_table","4":"part_coins","5":"part_surge","6":"part_clipboard"}
PART_INTRO={
 "1":"시장은 매일 흔들렸습니다. 하지만 더 자주 흔들린 것은 제 기준이었습니다.",
 "2":"질문이 바뀌자, AI의 답보다 먼저 제 판단이 바뀌기 시작했습니다.",
 "3":"정답을 구하던 자리에, 저는 회의실을 만들기 시작했습니다.",
 "4":"계좌를 키운 것은 매수 버튼이 아니라, 사지 않은 결정들이었습니다.",
 "5":"이론이 아니라, 실전에서 가장 먼저 달라진 것들의 기록입니다.",
 "6":"이제, 오늘 당장 써볼 수 있는 질문으로 갑니다.",
}

# 본문 중간에 들어갈 개념도(설명 삽화) — 전 장.
CH_FIGURE={
 1:("fig_1","진짜 적은 시장이 아니라, 욕심과 공포 사이에서 흔들리는 ‘나’다."),
 2:("fig_2","같은 7천만 원도 기준이 있느냐에 따라 다른 계좌가 된다. (실제 수익률이 아닌 개념도)"),
 3:("fig_3","종목을 물을수록 판단이 아니라 ‘안심’만 반복해서 사게 된다."),
 4:("fig_4","‘무엇을 살까’ 대신 ‘무엇을 확인할까’로 물으면 판단의 순서가 생긴다."),
 5:("fig_5","좋은 기업과 좋은 주식은 다르다 — 기대가 가격에 이미 반영됐는지를 본다. (실제 수익률이 아닌 개념도)"),
 6:("fig_6","종목보다 시장·섹터가 먼저다 — 돈의 흐름을 위에서 아래로 읽는다."),
 7:("fig_7","AI에게 결정을 맡기면 점쟁이, 관점을 물으면 투자위원회가 된다."),
 8:("fig_8","장전에는 종목을 찾기 전에 ‘오늘의 태도’부터 정한다."),
 9:("fig_9","계좌는 결과를, 기록은 이유를 남긴다 — 그 이유가 다음을 바꾼다."),
 10:("fig_10","현금은 노는 돈이 아니라, 다음 판단을 살 수 있는 ‘선택권’이다."),
 11:("fig_11","익절은 상승을 포기하는 게 아니라, 다음 판단을 위한 시간을 사는 일."),
 12:("fig_12","포트폴리오는 내가 어떤 미래에 베팅하는지 보여주는 ‘욕망의 지도’다."),
 13:("fig_13","같은 급등도 유형을 나누면, 추격할지 기다릴지 보낼지가 보인다."),
 14:("fig_14","가격이 빠졌다는 사실보다, 하락의 ‘성격’을 먼저 나눈다."),
 15:("fig_15","같은 리포트도 넓게(지형도)와 좁게(트리거)로 나눠 읽는다."),
 16:("fig_16","결론을 재촉하는 닫힌 질문은, 안심만 사고 판단을 남기지 못한다."),
 17:("fig_17","좋은 질문 하나가 실적·가격·리스크·반증으로 판단을 펼쳐준다."),
 18:("fig_18","종목을 찾기 전, 5분이면 오늘의 작전 회의가 끝난다."),
 19:("fig_19","계좌만 보지 않고 하루를 기록하면, 오늘이 내일로 이어진다."),
}
GVIS={'figure','compare','cards','flow','modebar','dodont'}  # 본문 중간으로 재배치 대상
APPENDIX_USAGE={
 "A":"1부 독자가 바로 써볼 수 있는 기본 질문입니다. 종목·시장·계좌 상황에 맞게 골라, 결론을 재촉하지 말고 ‘무엇을 확인할지’를 묻는 데 쓰세요.",
 "B":"장 시작 전 5분, 오늘이 공격할 날인지 지킬 날인지 ‘태도’를 먼저 정하는 용도입니다. 모두 채우기보다 오늘의 한 줄 판단을 잡는 데 목적이 있습니다.",
 "C":"장 마감 후, 수익률이 아니라 ‘오늘 판단의 질’을 남기는 기록지입니다. 매일 같은 양식으로 쌓으면 하루의 등락이 흐름으로 보이기 시작합니다.",
 "D":"매수 버튼을 누르기 전 3분 동안 쓰는 용도입니다. 완벽히 채우기보다, 지금 내가 감정으로 매수하려는 건 아닌지 확인하는 데 목적이 있습니다.",
 "E":"매도 버튼을 누르기 전 쓰는 용도입니다. 공포로 도망치는 매도인지, 기준에 따른 매도인지 구분하는 데 목적이 있습니다.",
}

# 장별 그래픽 (요소 목록). 핵심 박스 직후에 삽입된다.
def graphics_for(n):
    G={
    1:[('callout',"이 장을 한눈에 — 진짜 적은 ‘기준 없는 나’","시장 탓을 하던 손실의 진짜 원인은, 기준 없이 감정에 반응하던 제 자신이었습니다."),
       ('cards',[("오르면","더 오를 것 같아 못 판다."),
                 ("빠지면","더 빠질 것 같아 못 산다."),
                 ("수익 나면","더 먹고 싶어 욕심이 난다."),
                 ("손실 나면","인정하기 싫어 버틴다.")])],
    2:[('callout',"이 장을 한눈에 — 7천만 원에 필요한 건 종목이 아니라 기준","같은 계좌도 기준이 있느냐 없느냐에 따라 전혀 다른 계좌가 됩니다."),
       ('compare',("","기준이 없을 때","기준이 있을 때"),
        [("매수 이유","남이 사니까·뉴스 보고","미리 정한 조건이 충족돼서"),
         ("하락하면","불안에 손절·물타기","시나리오대로 대응"),
         ("계좌","감정에 휘둘린다","흔들려도 중심을 잡는다")],True,"기준이 있으면, 흔들려도 같은 자리로 돌아옵니다.")],
    3:[('callout',"이 장을 한눈에 — 종목을 물으면 ‘정답지 사용자’가 된다","AI에게 종목을 묻는 순간, 투자자가 아니라 정답을 받아 적는 사람이 됩니다."),
       ('cards',[("확증 편향","듣고 싶은 답만 골라 듣는다."),
                 ("책임 전가","틀리면 AI 탓으로 돌린다."),
                 ("맥락 상실","내 계좌·기준이 빠진 답을 받는다."),
                 ("허락받기","판단이 아니라 안심을 산다.")]),
       ('compare',("","AI를 잘못 쓰는 방식","AI를 제대로 쓰는 방식"),
        [("","결론을 요구한다","판단 구조를 요구한다"),
         ("","확신을 얻으려 한다","빠뜨린 질문을 찾는다"),
         ("","종목명을 던진다","조건과 반증을 나눈다"),
         ("","허락을 구한다","기준을 만든다")],True,"AI는 결론이 아니라 ‘판단 구조’를 물을 때 쓸모가 커집니다.")],
    6:[('callout',"이 장을 한눈에 — 종목보다 시장·섹터가 먼저 움직인다","돈은 늘 어딘가로 이동합니다. 위에서 아래로 흐름을 읽으면 종목이 다르게 보입니다."),
       ('flow',[("시장","위험선호인가, 위험회피인가 — 큰 방향"),
                ("섹터","돈이 지금 어느 업종으로 이동하는가"),
                ("종목","그 흐름 안에서 비로소 종목을 고른다")])],
    4:[('callout',"종목 질문 → 시스템 질문","같은 상황도 ‘무엇을 살까’가 아니라 ‘무엇을 확인할까’로 물으면 판단의 순서가 생깁니다."),
       ('compare',("","종목 질문","시스템 질문"),
        [("묻는 법","“이거 살까요?”","“사려면 무엇을 확인해야 하나요?”"),
         ("AI의 답","매수·매도 결론","확인 순서와 조건"),
         ("남는 것","그때뿐인 안심","반복 가능한 기준")],True,"질문을 바꾸면 AI의 답도 달라집니다.")],
    5:[('compare',("","좋은 기업","좋은 주식"),
        [("판단 대상","사업 자체 — 매출·이익·경쟁력","그 사업에 매겨진 가격"),
         ("좋다는 뜻","실적이 늘고 산업이 큰가","지금 가격이 기대 대비 싼가"),
         ("흔한 함정","좋으면 언제 사도 된다","모두가 좋다고 아는 값에 산다"),
         ("핵심 질문","사업적으로 좋은가?","이 기대는 이미 주가에 있나?")],False,"좋은 기업인지와 ‘지금 좋은 주식인지’를 분리해서 봅니다.")],
    7:[('compare',("","정답지로 쓸 때","회의실로 쓸 때"),
        [("AI의 역할","정답을 내려주는 점쟁이","관점을 넓혀주는 참석자"),
         ("내가 하는 일","결정을 떠넘긴다","근거를 받아 내가 결정한다"),
         ("질문 형태","“살까요, 팔까요?”","“이 판단의 약점은?”"),
         ("틀렸을 때","AI 탓을 한다","내 기준을 다시 본다")],True,"AI는 정답지가 아니라 ‘회의실’로 쓸 때 힘을 냅니다.")],
    8:[('modebar',[("공격","적극 신규·증액"),("정찰","소량 관찰"),("유지","현 비중"),
                   ("감량","리스크 축소"),("현금대기","기회 대기")])],
    9:[('flow',[("오늘 시장 한 줄 판단","오늘은 어떤 성격의 장이었나"),
                ("강·약 섹터 정리","어디로 돈이 들고 났나"),
                ("내 계좌 vs 시장","시장보다 강했나 약했나"),
                ("판단 vs 감정","기준에 따른 매매였나"),
                ("내일 체크포인트","먼저 확인할 질문 3개")])],
    10:[('cards',[("방어","하락장에서 계좌를 지키는 완충재."),
                  ("선택권","좋은 기회가 왔을 때 살 수 있는 권리."),
                  ("심리 안정","흔들릴 때 버티게 하는 여유."),
                  ("교체 재원","더 나은 종목으로 갈아탈 실탄.")])],
    11:[('compare',("","익절 = 배신","익절 = 시간 사기"),
        [("느낌","상승을 포기한 손해","다음 판단을 위한 여유 확보"),
         ("이후 행동","후회하며 재진입","현금으로 다음 기회 대기"),
         ("기준","주가만 본다","보유 논리와 비중을 본다")],True,"익절은 손해가 아니라, 다음 판단을 위한 준비입니다.")],
    12:[('cards',[("섹터 쏠림","한 방향에 베팅이 몰려 있지 않은가."),
                  ("현금 여력","다음 기회에 대응할 현금이 있는가."),
                  ("손실 방치","논리가 깨진 종목을 버티고만 있지 않은가."),
                  ("수익 과대","한 종목 비중이 계좌를 지배하지 않는가.")])],
    13:[('cards',[("뉴스형","재료에 반응한 급등. 재료 소멸 시 되돌림."),
                  ("수급형","특정 매수세가 만든 급등. 지속성이 관건."),
                  ("섹터형","섹터 전체의 급등. 흐름 시작일 수도, 낙폭 반등일 수도."),
                  ("실적형","실적이 뒷받침된 급등. 근거가 단단함."),
                  ("과열형","마지막 불꽃. 기대가 과도하게 반영된 구간.")])],
    14:[('cards',[("단순 조정","추세 안의 일시적 되돌림. 보유 논리 유지."),
                  ("섹터 약화","섹터 전체가 식는 신호. 비중 점검."),
                  ("종목 고유 문제","그 기업만의 악재. 보유 근거 재검토."),
                  ("시장 위험회피","시장 전체가 위험을 줄이는 국면. 현금·방어 우선.")])],
    15:[('compare',("","지형도용 읽기","트리거용 읽기"),
        [("목적","산업·판도 이해","단기 매매 신호 포착"),
         ("보는 곳","구조·경쟁력·장기 전망","목표가·서프라이즈·수급"),
         ("질문","“판이 어떻게 바뀌나?”","“지금 무엇이 달라졌나?”")],True,"같은 리포트도 목적에 따라 다르게 읽습니다.")],
    16:[('dodont',"이렇게 묻지 마라",
        [("정답 요구","“이거 살까요?”처럼 결정을 떠넘기는 질문"),
         ("허락 요구","“들고 가도 되죠?”처럼 안심을 구하는 질문"),
         ("예측 요구","“내일 오를까요?”처럼 점괘를 바라는 질문"),
         ("단답 유도","근거 없이 결론만 내게 하는 질문")],"dont")],
    17:[('dodont',"이렇게 물어라",
        [("조건을 묻기","“매수하려면 무엇을 확인해야 하나요?”"),
         ("분리해 묻기","“좋은 기업인지와 좋은 주식인지 나눠줘”"),
         ("반증을 묻기","“이 판단이 틀렸다고 볼 조건은?”"),
         ("선택지로 묻기","“추격·눌림대기·관찰·보내기 중 어디?”")],"do")],
    18:[('flow',[("오늘의 태도","공격·정찰·유지·감량·현금대기 중 하나"),
                 ("밤사이 글로벌","미국·금리·환율 분위기 확인"),
                 ("유리한 쪽","코스피·코스닥·대형·성장·방어 중 어디"),
                 ("오늘 볼 섹터 3개","내가 좋아하는 게 아니라 시장이 볼 섹터"),
                 ("계좌 점검","내 비중과 오늘 시장 방향이 맞는가")])],
    19:[('compare',("","계좌만 볼 때","기록할 때"),
        [("무엇을 보나","수익률 숫자","오늘 판단의 질"),
         ("남는 것","기분(좋다·나쁘다)","이유와 교훈"),
         ("내일","또 즉흥 매매","확인할 체크포인트 3개")],True,"계좌는 결과를, 기록은 이유를 남깁니다.")],
    }
    # 콜아웃(요약 박스)은 제외하고 시각 인포그래픽만 본문 중간에 배치
    return [g for g in G.get(n, []) if g[0]!='callout']

# ---------- 텍스트 정제 ----------
def clean(t):
    t=re.sub(r'\\(?=[^\w\s])','',t)
    t=re.sub(r'[ \t]*\n[ \t]*',' ',t)
    t=re.sub(r'\s{2,}',' ',t).strip()
    return t

def split_blocks(md):
    return [b for b in re.split(r'\n\s*\n', md)]

# ---------- 파싱 → 요소 목록 ----------
def parse():
    raw=SRC.read_text(encoding="utf-8")
    lines=raw.split("\n")
    def idx(p):
        for i,l in enumerate(lines):
            if l.startswith(p): return i
        return -1
    body_md="\n".join(lines[idx("# 1부."):idx("# 부록")])
    appendix_md="\n".join(lines[idx("## 부록 A."):])

    E=[]
    E.append(('cover',))
    E.append(('disclaimer', DISCLAIMER))
    E.append(('toc',))
    # 프롤로그
    E.append(('h1big','prologue','나는 AI에게 종목을 묻지 않기로 했습니다','chat_q'))
    E.append(('keysentence', PROLOGUE_KEY, 'chat_q'))
    E.append(('ornament',))
    for i,p in enumerate(PROLOGUE):
        E.append(('para', p, i==0))
        if i==4:  # '질문을 바꿨습니다' 문단 뒤에 before/after 인포그래픽
            E.append(('compare',("","바꾸기 전 질문","바꾼 뒤 질문"),
                [("종목","“이 종목 살까요?”","“사려면 무엇을 확인해야 하나요?”"),
                 ("예측","“내일 오를까요?”","“어떤 조건에서 오르고, 언제 틀린 건가요?”"),
                 ("기업","“좋은 기업인가요?”","“지금 좋은 주식인가요?”")],True,"질문이 바뀌면 AI의 답도 달라집니다."))
    # 본문
    E += parse_body(body_md)
    # 부록
    E += parse_appendix(appendix_md)
    # 책을 닫는 한 문장
    E.append(('closing', "좋은 투자는 정답을 찾는 일이 아니라, 끝까지 질문을 놓치지 않는 일입니다."))
    # 뒷부속: 저자 소개 + 판권지
    E.append(('authorbio', AUTHOR, AUTHOR_BIO))
    E.append(('colophon', [
        ("제목", TITLE), ("부제", SUBTITLE), ("지은이", AUTHOR),
        ("발행", f"{PROJECT} (자가출판)"), ("발행일", PUBDATE), ("문의", EMAIL),
    ]))
    return relocate(E)

# ---------- 인포그래픽/삽화를 '관련 문단' 옆으로 재배치 ----------
def _keywords(el):
    t=el[0]; ks=[]
    if t=='compare': ks=[el[1][1],el[1][2]]+[r[0] for r in el[2]]+[c for r in el[2] for c in r[1:]]
    elif t in ('cards','flow','modebar'): ks=[x[0] for x in el[1]]
    elif t=='dodont': ks=[x[0] for x in el[2]]
    elif t=='figure': ks=[el[2]]
    out=[]
    for k in ks:
        k=re.sub(r'[“”"\'(),.?·—×✕✓≠]',' ',k)
        for tok in k.split():
            if len(tok)>=2: out.append(tok)
    return out

_INSIGHT=['아니라','아니었','바뀌','달라졌','배웠','선택권','기준','깨달','중요','보이기 시작','시작했']
def pick_pullquote(paras, exclude=()):
    if isinstance(exclude,str): exclude=(exclude,)
    exclude=set(x for x in exclude if x)
    text=" ".join(paras)
    sents=[s.strip() for s in re.split(r'(?<=다\.)|(?<=요\.)', text) if s.strip()]
    best=None; bs=-1
    for s in sents:
        if not s.endswith('다.'): continue
        if any(c in s for c in '?“”"'): continue
        if s in exclude: continue
        L=len(s)
        if L<14 or L>44: continue
        sc=sum(2 for w in _INSIGHT if w in s) - abs(L-25)*0.05
        if '아니라' in s or '아니었' in s: sc+=1.5
        if s[:3] in ('그래서','그리고','그러다','하지만','그런데'): sc-=1.2
        if '이런 식' in s or '이렇게' in s: sc-=1.0
        if sc>bs: bs=sc; best=s
    return best if bs>0 else None

def relocate(E):
    out=[]; i=0; n=len(E)
    while i<n:
        el=E[i]
        if el[0]!='chapter':
            out.append(el); i+=1; continue
        j=i+1
        region=[]
        while j<n and E[j][0] not in ('chapter','part','h1big'):
            region.append(E[j]); j+=1
        vis=[e for e in region if e[0] in GVIS]
        rest=[e for e in region if e[0] not in GVIS]
        para_idx=[k for k,e in enumerate(rest) if e[0]=='para']
        if vis and para_idx:
            _BAD=('그 ','이 ','저 ','그래서','그리고','그러자','그제야','그것','이것','그런데')
            def good_after(k):  # 삽입 뒤 문단이 앞 문장을 이어받지 않도록(흐름 끊김 방지)
                nxt = rest[k+1] if k+1 < len(rest) else None
                if nxt and nxt[0]=='para':
                    s=nxt[1].lstrip()
                    return not any(s.startswith(b) for b in _BAD)
                return True
            # 후보 문단: 첫 문단 제외 + 앞~중간(앞 50%)으로 제한 → 너무 뒤로 안 감
            hi=max(3, int(len(para_idx)*0.5))
            front=para_idx[1:hi] or para_idx[1:] or para_idx
            used=set(); placements=[]
            for vi,v in enumerate(vis):
                kws=_keywords(v); best=None; bs=-1
                for k in front:
                    if k in used or not good_after(k): continue
                    sc=sum(rest[k][1].count(w) for w in kws)
                    if sc>bs: bs=sc; best=k
                if best is None or bs<=0:
                    cand=[k for k in front if k not in used and good_after(k)] \
                         or [k for k in front if k not in used] or front
                    best=cand[(vi*len(cand))//max(1,len(vis))]
                used.add(best); placements.append((best,v))
            # 발췌 인용구(pull-quote): 장 후반(~70%) 별도 문단 사이에
            ks=next((e[1] for e in region if e[0]=='keysentence'), "")
            pq=pick_pullquote([rest[k][1] for k in para_idx], exclude=ks)
            if pq:
                anchor=para_idx[min(len(para_idx)-1, int(len(para_idx)*0.7))]
                cand=[k for k in para_idx if k not in used and good_after(k)] \
                     or [k for k in para_idx if k not in used]
                if cand:
                    tgt=min(cand, key=lambda k:abs(k-anchor))
                    used.add(tgt); placements.append((tgt, ('pullquote', pq)))
            for k,v in sorted(placements, key=lambda x:-x[0]):
                rest.insert(k+1, v)
            region=rest
            # 장 끝 '한 줄 정리' — 핵심·발췌·닫는 문장으로 2~3줄 요약
            tail=[rest[k][1] for k in range(len(rest)) if rest[k][0]=='para'][-4:]
            end=pick_pullquote(tail, exclude=(ks, pq))
            summ=[]
            for s in (ks, pq, end):
                if s and s not in summ: summ.append(s)
            if summ: region=region+[('endnote', summ[:3])]
        out.append(el); out.extend(region); i=j
    return out

def parse_body(md):
    E=[]; buf=[]; cur=None; need_dropcap=[False]
    def flush():
        nonlocal buf
        if buf:
            txt=" ".join(buf).strip()
            if txt:
                E.append(('para', txt, need_dropcap[0]))
                need_dropcap[0]=False
            buf=[]
    for blk in split_blocks(md):
        raw=blk.strip()
        if not raw: continue
        m=re.match(r'^# (\d)부\. (.+)$', raw, re.S)
        if m: flush(); E.append(('part', m.group(1), clean(m.group(2)), PART_ICON.get(m.group(1),''), PART_INTRO.get(m.group(1),''))); cur=None; continue
        m=re.match(r'^# 에필로그\. (.+)$', raw, re.S)
        if m: flush(); E.append(('h1big','epilogue',clean(m.group(1)),'flag')); cur=None; need_dropcap[0]=True; continue
        m=re.match(r'^## (\d+)장\. (.+)$', raw, re.S)
        if m:
            flush(); cur=int(m.group(1)); E.append(('chapter', cur, clean(m.group(2)), CH_ICON.get(cur,''))); continue
        if raw.startswith("핵심 문장"):
            flush()
            ks=re.sub(r'^핵심\s*문장\s*\|\s*','', clean(raw))  # 정제 후 접두어 제거
            E.append(('keysentence', ks, CH_ICON.get(cur,'')))
            for g in graphics_for(cur): E.append(g)
            if cur in CH_FIGURE:
                fig=CH_FIGURE[cur]; E.append(('figure', fig[0], fig[1]))
            E.append(('ornament',))
            need_dropcap[0]=True
            continue
        if re.match(r'^\*\*[^*]+\*\*$', raw):
            flush(); E.append(('h3', raw.strip('*'))); continue
        if re.match(r'^[-*]\s+', raw):
            flush(); E.append(('bullets', [clean(x) for x in re.findall(r'(?m)^[-*]\s+(.+)$', raw)])); continue
        buf.append(clean(raw))
        if len(" ".join(buf))>=300: flush()
    flush()
    return E

def parse_appendix(md):
    md=re.sub(r'(?s)<table>.*?</table>\s*','',md)
    subs=re.split(r'(?m)^## (부록 [A-E]\. .+)$', md)
    E=[]; it=iter(subs[1:])
    for title in it:
        content=next(it)
        letter=title.split()[1].rstrip('.')
        E.append(('h1big','appendix', clean(title.strip()), 'clipboard'))
        if letter in APPENDIX_USAGE: E.append(('apxnote', APPENDIX_USAGE[letter]))
        E += parse_appendix_body(content, letter)
    return E

def parse_appendix_body(content, letter):
    E=[]; qmode=letter in ("A","D","E"); pending=False
    for blk in split_blocks(content):
        p=blk.strip()
        if not p: continue
        mcat=re.match(r'^\*\*\((\d)\)\s*(.+?)\*\*$', p, re.S)
        if mcat: E.append(('cat', mcat.group(1), clean(mcat.group(2)))); pending=False; continue
        mq=re.match(r'^\*\*(\d+)\.\s*(.+?)\*\*$', p, re.S)
        if mq: E.append(('q', qmode, mq.group(1), clean(mq.group(2)))); pending=(letter=="A"); continue
        msub=re.match(r'^\*\*(.+?)\*\*$', p, re.S)
        if msub: E.append(('h3', clean(msub.group(1)))); pending=False; continue
        if p.endswith(":") and len(p)<=16 and "\n" not in p:
            E.append(('fill', p[:-1])); continue
        # 라벨 + 밑줄 작성란이 한 블록인 경우: 라벨 + 작성선으로 분리
        ml=re.match(r'^(.{1,16}):\s*\n([\\_\s]+)$', p)
        if ml and set(re.sub(r'[\\\s]','',ml.group(2)))<=set('_'):
            E.append(('fill', ml.group(1))); E.append(('writeline',)); continue
        # 순수 밑줄 작성란(\_\_\_) → 깨끗한 작성선 (개행·공백·역슬래시 무시)
        t2=re.sub(r'[\\\s]','',p)
        if t2 and set(t2)<=set('_') and len(t2)>=3:
            E.append(('writeline',)); continue
        if re.search(r'(?m)^[-*]\s+', p):
            items=re.findall(r'(?m)^[-*]\s+(.+)$', p)
            if items: E.append(('bullets', [clean(x) for x in items])); continue
        if re.search(r'(?m)^\d+\.\s', p):
            items=re.findall(r'(?m)^(\d+)\.\s+(.+)$', p)
            if items: E.append(('numlist', [(num, clean(x)) for num,x in items])); continue
        text=clean(p)
        if pending: E.append(('prompt', text)); pending=False
        else: E.append(('para', text, False))
    return E
