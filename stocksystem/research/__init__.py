"""검증 계층 — 점수가 실제로 미래 수익률을 예측하는지 측정한다.

이 시스템의 모든 점수(기술·펀더멘털·종합)는 '그럴듯한 규칙'으로 만들어졌을
뿐, 지금까지 예측력이 측정된 적이 없었다. 이 패키지는 그 공백을 메운다.

  from stocksystem.research import run_event_study
  res = run_event_study(symbols, provider, cfg)
  print(res.report())
"""
from .eventstudy import (
    SCORERS, BucketStat, EventStudyResult, HorizonResult,
    analyze_panel, bonferroni_t, build_panel, compare_scorers,
    forward_excess, run_event_study,
)

__all__ = ["SCORERS", "BucketStat", "EventStudyResult", "HorizonResult",
           "analyze_panel", "bonferroni_t", "build_panel", "compare_scorers",
           "forward_excess", "run_event_study"]
