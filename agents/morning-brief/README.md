# 🌅 모닝브리핑 (morning-brief) — 매일 아침 주식 브리핑 에이전트

매일 아침 8시, `watchlist.txt`의 관심종목(미국+한국 혼용)과 시장 상황을 심층 분석해
`reports/모닝브리핑_{날짜}.md` 한국어 브리핑을 자동 생성합니다.

- 수치: 본 저장소 `stocksystem` 모듈이 계산 (종합점수·기술지표·펀더멘털·헤게모니·몬테카를로)
- 해설: LLM 폴백 체인 (Claude → Gemini → GPT → Grok — 키 있는 것만, 전부 실패 시 모듈 데이터만)
- 한국주식: 6자리 코드 자동 판정(.KS→.KQ) + 네이버 보강(PER·외국인 수급) + 코스피·코스닥 시장맥락
- 데이터 실패 시: 샘플 폴백 + 브리핑 최상단 ⚠️ 경고 (조용한 품질 저하 차단)

## 설치 (Windows)

```bat
:: 1) 저장소 루트에서 의존성 설치 (최초 1회)
pip install -r requirements.txt
pip install anthropic

:: 2) LLM 키 설정 (선택 — 없어도 모듈 해설로 동작)
copy agents\morning-brief\.env.example agents\morning-brief\.env
notepad agents\morning-brief\.env

:: 3) 바탕화면 바로가기 생성
powershell -ExecutionPolicy Bypass -File agents\morning-brief\install_shortcut.ps1

:: 4) 매일 아침 8시 자동 실행 등록
schtasks /Create /TN "morning-brief" /SC DAILY /ST 08:00 ^
  /TR "\"%CD%\agents\morning-brief\run-once.bat\""
```

macOS/Linux는 cron으로: `0 8 * * * cd /path/to/repo && python3 agents/morning-brief/brief.py`

## 사용

- 자동: 매일 08:00 작업 스케줄러가 실행
- 수동: 바탕화면 "모닝브리핑" 더블클릭 또는 `python agents/morning-brief/brief.py`
- 관심종목 변경: `watchlist.txt`를 메모장으로 수정 (한 줄 한 종목, 한국주식은 6자리 코드)

## 운영 한도 (MBO)

| 항목 | 값 |
|---|---|
| LLM 재시도 | 최대 3회 후 모듈 해설 폴백 |
| 1회 비용 | 500원 (초과 시 error.log 기록) |
| 월 누적 비용 | 15,000원 (도달 시 LLM 해설 생략) |
| 전체 실행 시간 | 10분 (초과 시 잔여 종목 생략 표기) |

## 운영 파일 (B 인프라 운영 루프)

- `history.json` — 실행 이력·비용 누적 (자동 생성, 최근 365회)
- `error.log` — 오류 기록
- 월 1회 두 파일을 열어 반복 오류·비정상 비용을 점검하세요. 버그·개선 요청은 GitHub Issues로.

> ⚠️ 본 에이전트는 교육·연구 목적입니다. 생성된 브리핑은 투자 자문이 아닙니다.
