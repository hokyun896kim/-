# 📦 BOM — /주식보고서 (Phase 3 발굴 + Phase 4 분해·검증)

## Phase 3 발굴 후보
| 후보 | 출처 | 5대 KPI | 판정 |
|---|---|---|---|
| stocksystem 분석 모듈 + cli.py | 사내 자산 (본 저장소) | 명료성✅ 충돌0✅ 최신✅ 의존성(요구사항 내)✅ 검증가능✅ | 채택 |
| 10섹션 프로 보고서 템플릿 | CFA/WSP 표준 | 명료성✅ 충돌0✅ 최신✅ 의존성0✅ 검증가능✅ | 재단 채택 |
| WebSearch 단독 데이터 수집 | tradermonty 등 공개 스킬 패턴 | 명료성✅ 충돌0✅ 최신✅ 의존성0✅ **검증가능❌(수치 부정확)** | 거부 |

## Phase 4 BOM 5분류
[🟢 정상 — 그대로 적용]
  • `cli.py analyze {T} --provider {yahoo|sample}` ← 사내:cli.py | 용도: 종합점수·기술·펀더멘털·근거 (미국·한국 공통)
  • `kr_hegemony.naver` (PER·외국인 지분율·기관/외국인 순매수) ← 사내:kr_hegemony/naver.py | 용도: 한국주식 보강 (best-effort)
  • `stocksystem.analysis.market.fear_greed` + `analyze_index` ← 사내:analysis/market.py | 용도: 시장 맥락 섹션
  • `stocksystem.analysis.sentiment` 경유 뉴스 분위기 (제공 시) ← 사내 | 용도: 뉴스 섹션 수치부
  • 면책 문구 ← 사내:README.md | 용도: 보고서 하단 고정

[🟡 재단 후 적용]
  • 10섹션 프로 템플릿 → 4섹션 리테일 템플릿(결론·근거·시장·뉴스/이벤트)으로 축약 ← CFA/WSP 표준
  • 데이터 신선도 원칙 → "기준일·데이터 소스 명기" 줄로 축약 ← Claude Cookbook

[🔴 걸러냄 — 적용 거부]
  • WebSearch 단독 수치 수집 ← 공개 스킬 패턴 | 사유: 수치 검증 불가, 사내 모듈로 대체
  • 등급 자의 보정(점수 외 의견 가공) | 사유: 등급 편향 함정 (리서치 트랙④)

[🏭 자체 작성 필요]
  • 한국주식 티커 정규화 (6자리 코드 → `.KS` 시도 → 실패 시 `.KQ`) + 통화 표기(₩/$) 분기 + 시장맥락 지수 분기(^KS11·^KQ11 / 나스닥·S&P) | 사유: PO 추가 요구 (2026-06-10), 기존 모듈에 없음
  • 실패 마커 감지 + 샘플 폴백 + ⚠️경고 로직 | 사유: yahoo 실패가 조용히 중립 보고서를 만드는 결함 실측 — 대체재 없음
  • 보고서 조립 절차(섹션→파일 저장→자가 점검 체크리스트) | 사유: stocksystem에 보고서 출력 기능 없음
  • 시장 브리핑 실행 스니펫(파이썬) | 사유: CLI에 시장 명령 없음 — 모듈 직접 호출 코드 필요

[🔵 공통 인프라]
  • 해당 없음 (단일 모드)

## Phase 5 Cross Validator 권고 반영 결정 (91→100 보완, 2026-06-10)
1. naver 보강 실패 시: 해당 줄만 "정보 없음" 표기, 섹션은 유지 (경고 플래그와 무관)
2. sentiment 모듈 미가용 시: 웹 검색 헤드라인 기반 정성 서술로 대체, 그것도 불가하면 "뉴스 수집 불가" 1줄 + 섹션 유지
3. 시장 브리핑 스니펫: SKILL.md에 실행 코드 전체 내장 (fear_greed(provider,cfg,market_symbol)→FearGreed(score,label,parts) / analyze_index(df,cfg,name)→MarketAnalysis)
4. .KS→.KQ 폴백 판정 기준: cli 출력에 "Failed to get ticker" 문자열 존재 또는 "현재가" 줄 부재 = 실패
5. SKILL.md 분량 예산: 전체 ~300줄 (절차 120 + 스니펫 60 + 템플릿 80 + 기타 40) — 500줄 이내 확정
6. WebSearch 불가 환경: 뉴스 섹션에 "⚠️ 웹 뉴스 수집 불가 — 모듈 데이터만 사용" 명시, 중단하지 않음
7. 같은 날 재실행: 동일 파일명 덮어쓰기 (절차에 명시)
