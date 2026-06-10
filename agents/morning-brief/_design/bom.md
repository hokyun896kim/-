# 📦 BOM — 모닝브리핑 에이전트 (Phase 3 발굴 + Phase 4 분해·검증)

## Phase 3 발굴 후보 5대 KPI
| 후보 | 출처 | 판정 |
|---|---|---|
| stocksystem 모듈 + /주식보고서 V1.2 심층 데이터 로직 | 사내 (QC 97/100 통과 자산) | 채택 🟢 |
| kr_hegemony.naver.enrich | 사내 | 채택 🟢 (best-effort) |
| 에신 본문 표준 자산 (install_shortcut.ps1 · verify_windows_adapter.ps1 · llm 폴백 패턴 · history.json 스키마) | 에신 SKILL.md V3.5 | 채택 🟢 |
| hgnx/automated-market-report (PDF 생성부) | GitHub | 거부 🔴 — PDF 의존성 다수 + 영어 전용, 마크다운으로 충분 |
| GitHub Actions 스케줄 (AlphaEdge 패턴) | GitHub | 거부 🔴 — 로컬 PC 데이터·파일 출력과 불일치 (Windows 작업 스케줄러 채택) |

## Phase 4 BOM 5분류
[🟢 정상 — 그대로 적용]
  • 심층 데이터 추출 로직 (technical.analyze·fundamental.analyze·hegemony·montecarlo·market.analyze_index·fear_greed) ← 사내:/주식보고서 V1.2 스니펫
  • kr_hegemony.naver.enrich ← 사내 | KR 종목 보강, 실패 시 "정보 없음"
  • install_shortcut.ps1 + verify_windows_adapter.ps1 + history.json/error.log 스키마 ← 에신 V3.5 표준 자산
  • 면책 문구 ← 사내:README.md

[🟡 재단 후 적용]
  • /주식보고서 V1.2 6섹션 템플릿 → 브리핑용 "시장 → 종목별 심층 섹션 → 일정 → 종합해설" 구조로 재단
  • 티커 정규화 (.KS→.KQ 폴백) ← 형제 스킬 — brief.py 함수로 코드화

[🔴 걸러냄 — 적용 거부]
  • PDF 리포트 생성부 (hgnx) | 사유: weasyprint 등 무거운 의존성, md로 충분
  • GitHub Actions 스케줄 | 사유: 로컬 파일 출력 요구와 불일치
  • 트레이딩 실행부 (AI-Trader류) | 사유: 범위 밖 — 브리핑 전용 (단일 책임)

[🏭 자체 제작 필요]
  • llm_providers.py — Claude→Gemini→GPT→Grok 폴백 체인 (V3.5 단일 모드 필수 부품) + 비용 가드(1회 500원·월 15,000원·재시도 3회)
  • brief.py — 본체: watchlist 파싱 → 종목별 수집(실패 스킵) → 시장(US/KR 자동 분기) → 조립 → LLM 해설(폴백: 모듈 narrative) → reports/ 저장 → history.json/error.log
  • watchlist.txt 파서 (미국 티커 + 6자리 한국 코드 혼용, # 주석 허용)
  • run-once.bat — Windows 어댑터 7룰 준수 (영문 echo·pushd %~dp0·chcp 65001·PYTHONUTF8)
  • skills/MB-01_morning_brief/SKILL.md — SSOT INSTRUCTION (LLM 해설 프롬프트 원본, A 승격 시 0 변경)

[🔵 공통 인프라]
  • 해당 없음 (단일 모드 — 단, llm_providers.py는 V3.5 룰에 따라 단일 모드 필수 🏭로 포함됨)

## 설계 결정
- 데이터 실패 판정: price_history 예외 또는 빈 DataFrame = 실패 → 종목별 sample 폴백 + ⚠️ 표기 (전 종목 실패 시 브리핑 최상단 전역 경고)
- 시장 맥락 분기: watchlist에 US 종목 있으면 미국 지수, KR 종목 있으면 코스피·코스닥 — 둘 다 있으면 둘 다
- 비용 추정: API usage 응답 토큰 수 × 단가로 history.json에 기록, 월 합산 후 한도 초과 시 LLM 생략
- 10분 한도: 시작 시각 기준, 초과 시 잔여 종목 스킵 + 표기
