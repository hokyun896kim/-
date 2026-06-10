---
description: "미국·한국 주식 1종목 심층 분석 보고서 제조 — 본 저장소 stocksystem 모듈(종합점수·기술·펀더멘털·시장맥락·뉴스분위기)과 kr_hegemony(한국 보강), 웹 최신 뉴스를 결합해 한국어 4섹션 보고서를 reports/ 폴더에 날짜별로 저장한다. 데이터 실패 시 샘플 폴백 + 최상단 경고. 사용자가 '주식보고서', '/주식보고서 AAPL', '/주식보고서 005930', '~종목 분석 보고서 만들어줘'를 요청할 때 사용."
user-invocable: true
version: "1.1"
last_updated: "2026-06-10"
---

<!-- 주식보고서_SPEC_VERSION: V1.1 (V1.0 + 한국주식 지원) -->

# /주식보고서 {티커} — 종목 심층 분석 보고서 제조

**미국·한국 주식 1종목을 검증된 사내 모듈 수치 + 웹 최신 뉴스로 분석해, 한국어 마크다운 보고서를 `reports/`에 날짜별로 누적한다.**

## 핵심 원칙

1. **수치는 모듈, 해설은 Claude** — 점수·지표는 stocksystem 모듈 출력을 무가공 인용한다. 등급을 자의로 올리거나 내리지 않는다 (애널리스트 등급 편향 방지).
2. **실패는 가시화** — 라이브 데이터 실패 시 조용히 진행하지 않는다. 샘플 데이터로 폴백하되 보고서 최상단에 ⚠️ 경고를 크게 표기한다.
3. **한국어 보고서 + 면책 의무** — 본문은 한국어, 모든 보고서 하단에 면책 문구 고정.
4. **매수·매도 근거 모두 표기** — 확증 편향 방지. 모듈이 출력한 긍정·부정 근거를 빠짐없이 싣는다.
5. **출처·기준일 명기** — 데이터 소스(yahoo/sample)와 생성 기준일을 보고서에 기록한다.

---

## Phase 0. 입력 해석 — 티커 정규화

인자에서 티커 1개를 받는다. 없으면 사용자에게 묻는다 (한 번 호출 = 한 종목 심층).

| 입력 형태 | 판정 | 정규화 |
|---|---|---|
| 영문 티커 (예: `AAPL`, `BRK-B`) | 미국주식 | 대문자 그대로 |
| 6자리 숫자 (예: `005930`) | 한국주식 | `{코드}.KS` 먼저 시도 → 실패 시 `{코드}.KQ` |
| `.KS`/`.KQ` 포함 (예: `005930.KS`) | 한국주식 | 그대로 |
| 회사명 (예: "삼성전자", "애플") | 검색 필요 | WebSearch로 티커 확인 후 위 규칙 적용 |

**국가별 분기 변수** (이후 Phase에서 사용):

| 변수 | 미국 | 한국 |
|---|---|---|
| 시장 지수 | `^IXIC`(나스닥)·`^GSPC`(S&P500)·`^DJI`(다우) | `^KS11`(코스피)·`^KQ11`(코스닥) |
| 공포·탐욕 기준 심볼 | `SPY` | `^KS11` |
| 통화 표기 | $ | ₩ (원) |
| 한국 보강 (naver) | 적용 안 함 | `kr_hegemony.naver.enrich` 적용 |

## Phase 1. 환경 준비

저장소 루트에서 실행. 의존성 미설치 시 1회 설치:

```bash
python3 -c "import pandas, yaml" 2>/dev/null || pip install -q -r requirements.txt
mkdir -p reports
```

## Phase 2. 데이터 수집 (실패 마커 감지 필수)

### 2a. 종목 분석 — cli.py (종합점수·기술·펀더멘털·근거)

```bash
python3 cli.py analyze {SYM} --provider yahoo --period 1y
```

**실패 판정 기준 (둘 중 하나면 실패)**: 출력에 `Failed to get ticker` 문자열이 있거나, `현재가` 줄이 없음.
- 한국주식 `.KS` 실패 → `.KQ`로 1회 재시도 (코스닥 종목).
- 최종 실패 → `--provider sample`로 재실행 + **경고 플래그 ON** (보고서 최상단 ⚠️ 표기). 샘플도 실패(형식 오류 등)하면 보고서를 만들지 않고 원인만 보고한다.

### 2b. 시장 브리핑 — 내장 스니펫 (국가별 지수 + 공포·탐욕)

```bash
python3 - "{PROVIDER}" "{COUNTRY}" << 'EOF'
import sys
from stocksystem.config import load_config
from stocksystem.data import get_provider
from stocksystem.analysis import market as mk

provider_name, country = sys.argv[1], sys.argv[2]   # yahoo|sample, US|KR
cfg = load_config(); provider = get_provider(provider_name)
idx = ([("^KS11", "코스피"), ("^KQ11", "코스닥")] if country == "KR"
       else [("^IXIC", "나스닥"), ("^GSPC", "S&P500"), ("^DJI", "다우")])
for sym, name in idx:
    try:
        df = provider.price_history(sym, period="2y")
        r = mk.analyze_index(df, cfg.technical, symbol=sym, name=name)
        print(f"[{name}] {r.price:,.2f} ({r.change_pct:+.2f}%) 방향성 {r.direction_score:.0f} {r.direction_label}")
        print(f"  추세: {r.trend}\n  모멘텀: {r.momentum}\n  수급: {r.supply}\n  변동성: {r.volatility}")
        for line in r.narrative: print(f"  {line}")
    except Exception as e:
        print(f"[{name}] 수집 실패: {e}")
try:
    fg = mk.fear_greed(provider, cfg.technical,
                       market_symbol="^KS11" if country == "KR" else "SPY")
    print(f"[공포탐욕] {fg.score:.0f} {fg.label} | 구성: {fg.components}")
except Exception as e:
    print(f"[공포탐욕] 수집 실패: {e}")
EOF
```

### 2c. 뉴스 분위기 + 실적·이벤트 — 내장 스니펫

```bash
python3 - "{PROVIDER}" "{SYM}" << 'EOF'
import sys
from stocksystem.data import get_provider
from stocksystem.analysis import sentiment as st

provider_name, sym = sys.argv[1], sys.argv[2]
provider = get_provider(provider_name)
try:
    news = provider.news(sym, limit=8)
    s = st.aggregate(news)
    print(f"[뉴스분위기] {s.score:.0f} {s.label} (기사 {s.n_articles}건, 긍정 {s.n_positive}/부정 {s.n_negative}, 신뢰도 {s.confidence})")
    for it in s.items[:5]:
        print(f"  • {it.title} ({it.publisher or '-'}, {it.published or '-'}, 감성 {it.sentiment})")
except Exception as e:
    print(f"[뉴스분위기] 수집 실패: {e}")
try:
    ev = provider.events(sym)
    print(f"[이벤트] 다음 실적발표: {ev.next_earnings_date or '정보 없음'} | 배당락: {ev.ex_dividend_date or '정보 없음'} | 배당금: {ev.dividend_amount or '정보 없음'}")
    for row in provider.earnings_history(sym, limit=4):
        sp = f"{row.surprise_pct:+.1f}%" if row.surprise_pct is not None else "-"
        print(f"  {row.period}: EPS 예상 {row.eps_estimate} → 실제 {row.eps_actual} (서프라이즈 {sp})")
except Exception as e:
    print(f"[이벤트] 수집 실패: {e}")
EOF
```

### 2d. 한국주식 보강 — kr_hegemony.naver (한국주식만, best-effort)

```bash
python3 - "{CODE6}" << 'EOF'
import sys; sys.path.insert(0, "kr_hegemony")
code6 = sys.argv[1]   # 6자리 코드 (예: 005930)
try:
    import naver
    d = naver.enrich(code6, days=20)
    print(f"[KR보강] {d}")
except Exception as e:
    print(f"[KR보강] 수집 실패: {e}")
EOF
```

- 실패해도 **중단하지 않는다**. 보고서 해당 줄에 "정보 없음"으로 표기 (경고 플래그와 무관 — naver 보강은 부가 정보).

### 2e. 웹 최신 뉴스 (보조)

WebSearch로 `{회사명} stock news` (한국주식은 `{회사명} 주가 뉴스`)를 1~2회 검색해 최근 1주 핵심 이슈 2~4건을 수집한다.
- WebSearch 불가 환경이면 뉴스 섹션에 "⚠️ 웹 뉴스 수집 불가 — 모듈 데이터만 사용" 1줄을 적고 진행한다.
- 웹 뉴스는 정성 서술에만 쓰고, 수치(주가·PER 등)는 절대 웹 검색값으로 적지 않는다 (모듈 수치만).

## Phase 3. 보고서 작성

`reports/주식보고서_{입력티커}_{YYYY-MM-DD}.md`로 저장한다. **같은 날 재실행 시 동일 파일명 덮어쓰기.**

````markdown
# 📈 주식 분석 보고서 — {회사명} ({티커})

> 생성일 {YYYY-MM-DD} · 데이터 소스: {yahoo 라이브 | sample} · 기간 1y
{경고 플래그 ON일 때만:}
> ## ⚠️ 라이브 데이터 수집 실패 — 아래 수치는 **합성 샘플 데이터** 기반입니다. 실제 투자 참고 금지.

## 1. 종합 평가
| 항목 | 값 |
|---|---|
| 현재가 | {₩ 또는 $}{값} |
| 종합점수 | {N.N} / 100 |
| 추천 등급 | {모듈 출력 그대로} |

**판단 근거** (모듈 출력 전체 — 긍정·부정 모두):
- {근거 줄들}

## 2. 기술적 + 펀더멘털 상세
- 기술점수 {N.N} — 신호: {추세/가격위치/RSI/MACD/볼린저 표}
- 펀더멘털 점수 {N.N}
{한국주식이면:} - 한국 보강 (네이버): PER {값|정보 없음} · 외국인 지분율 {값|정보 없음}% · 외국인/기관 순매수(20일) {값|정보 없음}

## 3. 시장 맥락
{2b 출력 — 지수별 방향성·추세·모멘텀·수급·변동성 + 해설(narrative)}
- 공포·탐욕 지수: {N} {라벨}
- **이 종목과의 연결**: {시장 국면 속에서 이 종목 점수를 1~3문장으로 해석}

## 4. 뉴스 분위기 + 실적·이벤트
- 뉴스 분위기 점수: {N} {라벨} (신뢰도 {값})
- 최근 헤드라인: {모듈 수집 헤드라인}
- 웹 최신 이슈: {2e 요약 — 출처 링크 포함, 불가 시 경고 1줄}
- 다음 실적발표: {D-day 표기} · 배당락 {날짜} · 최근 분기 서프라이즈 {표}

---
> ⚠️ **면책**: 본 보고서는 교육·연구 목적입니다. 제공되는 점수와 추천은 투자 자문이 아니며, 모든 투자 판단과 결과의 책임은 사용자 본인에게 있습니다.
````

**작성 규칙**:
- 수치는 Phase 2 모듈 출력만 사용. 해설(섹션 3 "연결", 섹션 4 정성 서술)은 수치와 모순되지 않게.
- 초보 투자자도 읽도록 용어는 풀어서 (예: "OBV(거래량 누적 흐름 — 매집/분산 판단)").
- 한국주식 통화는 ₩, 미국주식은 $. 샘플 폴백이더라도 국가 KR이면 현재가는 반드시 `₩{값} (샘플)` 형식으로 표기한다.

## Phase 4. 자가 점검 (보고서 저장 후 필수)

- [ ] 4개 섹션(종합/상세/시장/뉴스·이벤트) 모두 존재
- [ ] 폴백 사용 시 최상단 ⚠️ 경고 존재 (라이브 성공 시엔 경고 없어야 함)
- [ ] 면책 문구 존재
- [ ] 등급·점수가 모듈 출력과 일치 (자의 가공 없음)
- [ ] 파일이 `reports/`에 실제 저장됨 (`ls -la reports/`)
- [ ] 사용자에게 파일 경로 + 종합점수·등급 1줄 요약 보고

## 금지 사항

❌ 라이브 실패를 경고 없이 넘기기 (조용한 품질 저하 — 실측된 결함)
❌ 웹 검색값으로 수치(주가·PER·점수) 기재 — 수치는 모듈만
❌ 모듈 등급의 자의 상향/하향 ("매수"를 "강력 매수"로 바꾸는 등)
❌ 면책 문구 생략
❌ 티커 여러 개를 한 보고서에 욱여넣기 (한 호출 = 한 종목)
❌ 다른 스킬 호출에 의존 (자기완결 — 필요한 코드는 본문 스니펫에 내장됨)

## 사용 예시

```
/주식보고서 AAPL          # 미국주식
/주식보고서 005930        # 한국주식 (삼성전자 → 005930.KS 자동 판정)
/주식보고서 삼성전자       # 회사명 → 티커 검색 후 진행
```

## 필요 도구
Bash (cli.py·스니펫 실행) · Write (보고서 저장) · WebSearch (웹 뉴스 보조·티커 검색) · Read/Glob (저장 확인)
