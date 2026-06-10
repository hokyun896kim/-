# CLAUDE.md

## 스킬 레지스트리 (헌법 등재)
- `/주식보고서 {티커}` — 미국·한국 주식 1종목 심층 분석 보고서를 `reports/`에 생성 (.claude/skills/주식보고서/, V1.2, 2026-06-10 출하). 피드백·버그는 GitHub Issues로.
- `/skill-create-코어5` · `/에신-llm-dependent-agent-create` — 메타 스킬 (출처: SUNWOONGKYU/claude-meta-skills)

## 에이전트 레지스트리 (헌법 등재)
- **모닝브리핑** (하이브리드형: 수집+분석+생성) — 매일 08:00 관심종목(미국+한국)+시장 심층 브리핑을 `reports/`에 자동 생성 (agents/morning-brief/, 인프라 B 스케줄·트리거형, 2026-06-10 출하, QC 100/100). 운영 점검: history.json·error.log 월 1회.
