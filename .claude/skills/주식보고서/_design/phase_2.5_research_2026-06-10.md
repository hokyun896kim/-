# Phase 2.5 도메인 심층 리서치 요약 — 주식 분석 보고서 스킬 (M 규모)

## 4 트랙 조사

### ① 기존 스킬·솔루션 (6건)
- tradermonty/claude-trading-skills | github.com/tradermonty/claude-trading-skills | 강점: 시장분석·차트·스크리너 등 풀 스택 | 약점: 영어, WebSearch 의존 수치
- yennanliu/InvestSkill | github.com/yennanliu/InvestSkill | 강점: LLM 범용 | 약점: 데이터 정확도 보장 없음
- mcpmarket market-analysis / stock-analyzer 스킬 | mcpmarket.com | 강점: 4유형(기본/펀더멘털/기술/종합) 분기 | 약점: 외부 데이터 의존
- Claude Cookbook skills-financial-applications | platform.claude.com | 강점: 공식 패턴 (출처·날짜 명기 원칙) | 약점: 범용
- claude-office-skills stock-analysis | claudemarketplaces.com | 강점: 단순 | 약점: 보고서 이력 관리 없음
- **사내 자산 stocksystem** | 본 저장소 | 강점: 검증된 점수화·기술·펀더멘털·시장·감성 모듈 + 오프라인 샘플 | 약점: 보고서 출력 기능 없음 (CLI 텍스트만)

### ② 학술·표준 (4건)
- CFA Institute Equity Research Report Essentials — 일관 구조 + 정확성 원칙
- Wall Street Prep 표준 형식 — 개요·재무·리스크·밸류에이션 4축
- 10섹션 프로 템플릿 (Executive Summary~Conclusion) — 리테일용으로는 과함 → 4섹션 재단
- 데이터 신선도 원칙 — "최신 분기 명시 검색"이 범용 검색보다 정확

### ③ 사용자 워크플로우 (3건)
- PO 현재 워크플로우: 체계 없이 대시보드·검색을 오감, 기록 없음 (Phase 1 라운드 3 답변)
- 리테일 투자자 표준 여정: 종목 발견 → 점수 확인 → 근거 확인 → 시장 맥락 → 기록
- 반복 조회 패턴: 같은 종목을 시점 달리해 재조회 → 날짜별 파일 누적이 차별점

### ④ 실패 사례·교훈 (5건)
- 확증 편향: 애널리스트 첫인상이 ~36개월 지속 — 매수/매도 근거를 모두 표기해야 함
- 등급 편향: S&P500 애널리스트 의견 49%가 매수 vs 매도 6% — 모듈 점수 그대로 인용 (자의적 상향 금지)
- 경영진 가이던스 과신 — 본 스킬은 수치 기반 모듈 점수만 사용
- **자체 발견: yahoo 실패 시 조용한 품질 저하** — 크래시 없이 중립 50점 보고서 생성됨. 실패 마커 감지 필수 (본 환경 실측, 2026-06-10)
- 투자 자문 오인 리스크 — 면책 문구 의무화 (README 동일 취지)

## 종합 발견
- 패턴: ①점수+등급 결론부 ②근거 수치 표 ③시장 맥락 ④뉴스·이벤트 ⑤출처·날짜 명기
- 차별점 후보: 사내 검증 모듈 수치 (웹 검색 의존 스킬 대비 정확) · 날짜별 이력 누적 · 한국어 해설
- 함정: 조용한 데이터 실패 / 등급 자의 상향 / 면책 누락 / 거대 보고서화
- 적용 표준: 4섹션 구조 + 출처·기준일 명기 + 면책 문구

## 영향 (Phase 3~6)
- BOM: cli.py·stocksystem 모듈 🟢 / 10섹션 템플릿 🟡 재단 / 실패 감지 로직 🏭 자체 작성 / 웹검색 단독 수집 🔴 거부
- 헌법 제약: 한국어 보고서 · 면책 의무 · 점수 무가공 인용
