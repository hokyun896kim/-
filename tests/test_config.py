"""설정 로딩 및 프리셋 테스트."""
from stocksystem.config import load_config, Config
from stocksystem.data.universe import load_universe


def test_default_config_has_empty_presets():
    # presets 미지정 시 빈 dict (KeyError/None 아님)
    c = Config()
    assert c.presets == {}


def test_presets_load_from_yaml(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text(
        "watchlist: [AAPL]\n"
        "presets:\n"
        "  대형주: [NVDA, AVGO]\n"
        "  중소형주: [CAVA, FIX]\n",
        encoding="utf-8",
    )
    c = load_config(p)
    assert set(c.presets) == {"대형주", "중소형주"}
    assert c.presets["대형주"] == ["NVDA", "AVGO"]
    assert c.presets["중소형주"] == ["CAVA", "FIX"]


def test_missing_presets_defaults_to_empty(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text("watchlist: [AAPL]\n", encoding="utf-8")
    c = load_config(p)
    assert c.presets == {}


def test_project_config_has_minervini_presets():
    # 실제 config.yaml 에 보고서 10종목 프리셋이 들어 있는지
    c = load_config()
    joined = {t for v in c.presets.values() for t in v}
    for t in ["NVDA", "AVGO", "APP", "PLTR", "COST",
              "ALAB", "CAVA", "CELH", "VERX", "FIX"]:
        assert t in joined, f"{t} 누락"


def test_universe_contains_preset_tickers():
    # 스크리너가 분석할 수 있도록 유니버스에 신규 종목이 포함됐는지
    symbols = {u.symbol for u in load_universe()}
    for t in ["APP", "PLTR", "ALAB", "CAVA", "CELH", "VERX", "FIX"]:
        assert t in symbols, f"{t} 가 universe.csv 에 없음"
