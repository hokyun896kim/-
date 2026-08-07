"""섹터 상대평가 채점 검증.

절대 구간 채점이 만들던 편향(은행·통신 고득점, 고성장 기술주 감점)이
sector_neutral=True 에서 실제로 사라지는지 확인한다.
"""
from __future__ import annotations

import pytest

from stocksystem.analysis import fundamental as fa
from stocksystem.config import load_config
from stocksystem.data.base import Fundamentals


def _f(sym, sector, pe, pb, de, **kw):
    base = dict(return_on_equity=0.20, profit_margin=0.20,
                revenue_growth=0.10, earnings_growth=0.10,
                dividend_yield=0.01)
    base.update(kw)
    return Fundamentals(symbol=sym, name=sym, sector=sector, trailing_pe=pe,
                        price_to_book=pb, debt_to_equity=de, **base)


# 같은 섹터 안에서 상대적으로 싼 기술주 vs 비싼 기술주
TECH = [
    _f("CHEAPTECH", "Technology", 22, 5, 20),
    _f("MIDTECH1", "Technology", 30, 9, 30),
    _f("MIDTECH2", "Technology", 34, 11, 35),
    _f("MIDTECH3", "Technology", 38, 14, 40),
    _f("RICHTECH", "Technology", 55, 40, 25),
]
BANKS = [
    _f("BANK1", "Financial Services", 9, 1.1, 210),
    _f("BANK2", "Financial Services", 11, 1.4, 230),
    _f("BANK3", "Financial Services", 13, 1.8, 250),
    _f("BANK4", "Financial Services", 15, 2.2, 270),
    _f("BANK5", "Financial Services", 18, 2.6, 300),
]


def test_percentile_scores_lower_is_better():
    vals = {"A": 10.0, "B": 20.0, "C": 30.0}
    out = fa._percentile_scores(vals, lower_is_better=True)
    assert out["A"] == 100.0 and out["C"] == 0.0
    assert out["B"] == pytest.approx(50.0)


def test_percentile_scores_higher_is_better():
    vals = {"A": 10.0, "B": 20.0, "C": 30.0}
    out = fa._percentile_scores(vals, lower_is_better=False)
    assert out["A"] == 0.0 and out["C"] == 100.0


def test_percentile_scores_ties_share_average_rank():
    vals = {"A": 10.0, "B": 10.0, "C": 30.0}
    out = fa._percentile_scores(vals, lower_is_better=True)
    assert out["A"] == out["B"]


def test_percentile_scores_single_item_is_neutral():
    assert fa._percentile_scores({"A": 5.0}, True) == {"A": 50.0}


def test_absolute_scoring_favors_banks_over_tech():
    """현행(절대 구간) 채점의 편향을 명시적으로 기록한다."""
    tech = fa.analyze(TECH[4])            # RICHTECH, PER 55
    bank = fa.analyze(BANKS[0])           # BANK1, PER 9
    assert bank.score > tech.score
    assert bank.metric_scores["PER"] > tech.metric_scores["PER"]


def test_sector_neutral_scores_within_sector_only():
    """섹터 중립화 후에는 '섹터 안에서 싼가'만 남는다."""
    res = fa.analyze_cross_section(TECH + BANKS, sector_neutral=True,
                                   min_peers=4)
    by = {r.symbol: r for r in res}
    # 기술주 중 가장 싼 종목이 기술주 안에서 PER 만점
    assert by["CHEAPTECH"].metric_scores["PER"] == 100.0
    assert by["RICHTECH"].metric_scores["PER"] == 0.0
    # 은행 중 가장 싼 종목도 마찬가지로 자기 섹터 안에서 만점
    assert by["BANK1"].metric_scores["PER"] == 100.0
    assert by["BANK5"].metric_scores["PER"] == 0.0


def test_sector_neutral_removes_cross_sector_valuation_bias():
    """PER 55 기술주가 PER 18 은행보다 낮게 평가되던 문제가 사라져야 한다.

    CHEAPTECH(PER 22)는 절대 기준으로는 BANK5(PER 18)보다 비싸서 감점됐지만,
    섹터 중립화 후에는 각자 자기 섹터에서의 위치로 평가된다.
    """
    absolute = {r.symbol: r for r in fa.analyze_cross_section(
        TECH + BANKS, sector_neutral=False)}
    neutral = {r.symbol: r for r in fa.analyze_cross_section(
        TECH + BANKS, sector_neutral=True, min_peers=4)}

    # 절대 기준: 은행이 기술주보다 PER 점수가 높다
    assert absolute["BANK5"].metric_scores["PER"] > \
        absolute["CHEAPTECH"].metric_scores["PER"]
    # 섹터 중립: 각자 섹터 최저 PER 이므로 CHEAPTECH 가 역전한다
    assert neutral["CHEAPTECH"].metric_scores["PER"] > \
        neutral["BANK5"].metric_scores["PER"]


def test_sector_neutral_keeps_loss_makers_penalized():
    """적자(PER<=0)를 '가장 싸다'로 랭킹하면 안 된다."""
    items = list(TECH) + [_f("LOSSMAKER", "Technology", -5, 3, 50)]
    res = {r.symbol: r for r in fa.analyze_cross_section(
        items, sector_neutral=True, min_peers=4)}
    # 적자 기업은 절대 채점의 페널티(25점)를 그대로 유지
    assert res["LOSSMAKER"].metric_scores["PER"] == 25.0
    assert res["LOSSMAKER"].metric_scores["PER"] < \
        res["CHEAPTECH"].metric_scores["PER"]


def test_sector_neutral_falls_back_when_too_few_peers():
    """표본 3개짜리 백분위는 신뢰할 수 없으니 절대 구간을 유지한다."""
    few = TECH[:2] + BANKS[:2]
    neutral = {r.symbol: r for r in fa.analyze_cross_section(
        few, sector_neutral=True, min_peers=4)}
    absolute = {r.symbol: r for r in fa.analyze_cross_section(
        few, sector_neutral=False)}
    for s in neutral:
        assert neutral[s].metric_scores["PER"] == \
            absolute[s].metric_scores["PER"]


def test_sector_neutral_off_matches_analyze():
    for f in TECH:
        a = fa.analyze(f)
        b = fa.analyze_cross_section([f], sector_neutral=False)[0]
        assert a.score == b.score
        assert a.metric_scores == b.metric_scores


def test_unknown_sector_is_skipped_not_crashed():
    items = list(TECH) + [_f("NOSECTOR", None, 25, 6, 30)]
    res = {r.symbol: r for r in fa.analyze_cross_section(
        items, sector_neutral=True, min_peers=4)}
    # 섹터 미상 종목은 절대 채점 그대로, 나머지는 정상 상대평가
    assert res["NOSECTOR"].metric_scores["PER"] == fa.score_pe(25)
    assert res["CHEAPTECH"].metric_scores["PER"] == 100.0


# ----------------------------- 설정 -----------------------------
def test_fundamental_config_defaults_to_absolute():
    """기존 동작이 기본값이어야 한다 (검증 전에는 바꾸지 않는다)."""
    cfg = load_config()
    assert cfg.fundamental.sector_neutral is False
    assert cfg.fundamental.min_peers == 4


def test_fundamental_config_reads_yaml(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("fundamental:\n  sector_neutral: true\n  min_peers: 6\n",
                 encoding="utf-8")
    cfg = load_config(p)
    assert cfg.fundamental.sector_neutral is True
    assert cfg.fundamental.min_peers == 6


# ----------------------------- 스크리너 연동 -----------------------------
def test_apply_sector_neutral_is_noop_when_disabled():
    from stocksystem.analysis import scoring as sc
    from stocksystem.config import Config as C

    cfg = C()
    cfg.fundamental.sector_neutral = False
    results = [sc.StockAnalysis(
        symbol=f.symbol, name=f.symbol, total_score=50.0,
        recommendation="hold", recommendation_label="보유",
        fundamental=fa.analyze(f)) for f in TECH + BANKS]
    before = [r.fundamental.score for r in results]
    sc.apply_sector_neutral(results, cfg)
    assert [r.fundamental.score for r in results] == before


def test_apply_sector_neutral_rescores_and_reclassifies():
    from stocksystem.analysis import scoring as sc
    from stocksystem.config import Config as C

    cfg = C()
    cfg.fundamental.sector_neutral = True
    results = [sc.StockAnalysis(
        symbol=f.symbol, name=f.symbol, total_score=0.0,
        recommendation="hold", recommendation_label="보유",
        fundamental=fa.analyze(f)) for f in TECH + BANKS]
    sc.apply_sector_neutral(results, cfg)
    by = {r.symbol: r for r in results}
    # 펀더멘털만 있으므로 종합점수 = 펀더멘털 점수
    assert by["CHEAPTECH"].total_score == by["CHEAPTECH"].fundamental.score
    # 추천 라벨이 새 점수에 맞게 다시 매겨졌는지
    assert by["CHEAPTECH"].recommendation_label in sc.RECO_LABELS.values()
    # 섹터 내 최저 PER 이 최고 PER 보다 높은 점수
    assert by["CHEAPTECH"].total_score > by["RICHTECH"].total_score


def test_apply_sector_neutral_skips_when_too_few_symbols():
    from stocksystem.analysis import scoring as sc
    from stocksystem.config import Config as C

    cfg = C()
    cfg.fundamental.sector_neutral = True
    results = [sc.StockAnalysis(
        symbol=f.symbol, name=f.symbol, total_score=50.0,
        recommendation="hold", recommendation_label="보유",
        fundamental=fa.analyze(f)) for f in TECH[:2]]
    before = [r.fundamental.score for r in results]
    sc.apply_sector_neutral(results, cfg)
    assert [r.fundamental.score for r in results] == before
