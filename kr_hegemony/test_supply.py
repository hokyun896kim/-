"""수급 집계·라벨 로직 오프라인 테스트 (pykrx 네트워크 불필요)."""
import pandas as pd
import supply


def _df(rows):
    """투자자별 순매수 mock (index=투자자, columns=[매도,매수,순매수])."""
    idx, net = zip(*rows)
    return pd.DataFrame({"매도": [0]*len(rows), "매수": [0]*len(rows),
                         "순매수": list(net)}, index=list(idx))


def test_agg_foreign_and_inst():
    df = _df([("개인", -500), ("외국인", 300), ("기타외국인", 50),
              ("기관합계", 150), ("전체", 0)])
    f, i = supply._agg_net(df)
    assert f == 350    # 외국인 300 + 기타외국인 50
    assert i == 150


def test_agg_missing_rows():
    df = _df([("개인", 100), ("전체", 100)])
    f, i = supply._agg_net(df)
    assert f is None and i is None


def test_label_dual_accumulation():
    assert "쌍끌이" in supply.supply_label(300, 150)


def test_label_foreign_only():
    assert supply.supply_label(300, -50) == "🟢 외국인 매집"


def test_label_inst_only():
    assert "기관 매집" in supply.supply_label(-200, 100)


def test_label_dual_sell():
    assert "이탈" in supply.supply_label(-300, -100)


def test_label_unknown():
    assert "미확인" in supply.supply_label(None, None)


def test_eok_conversion():
    assert supply._eok(35_000_000_000) == 350.0   # 350억
    assert supply._eok(None) is None


def test_per_from_df_filters_nonpositive():
    df = pd.DataFrame({"PER": [12.34, -5.0, 0.0, 8.9]},
                      index=["005930", "000660", "035720", "68270"])
    out = supply._per_from_df(df)
    assert out["005930"] == 12.3            # 반올림
    assert "000660" not in out             # 적자(-5) 제외
    assert "035720" not in out             # 0 제외
    assert "68270" not in out and out["068270"] == 8.9   # 6자리 zero-fill


def test_netmap_picks_value_column_and_converts_to_eok():
    # '순매수거래대금' 우선 선택, 원→억 변환
    df = pd.DataFrame({"순매수거래량": [10, 20],
                       "순매수거래대금": [35_000_000_000, -12_000_000_000]},
                      index=["005930", "000660"])
    out = supply._netmap_from_df(df)
    assert out["005930"] == 350.0
    assert out["000660"] == -120.0


def test_netmap_fallback_to_any_net_column():
    df = pd.DataFrame({"순매수": [50_000_000_000]}, index=["207940"])
    out = supply._netmap_from_df(df)
    assert out["207940"] == 500.0


def test_netmap_empty_when_no_net_column():
    df = pd.DataFrame({"매수": [1], "매도": [2]}, index=["005930"])
    assert supply._netmap_from_df(df) == {}
