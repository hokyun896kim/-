"""차트 판독 엔진 테스트 (미너비니 SEPA/VCP · 네트워크/API 키 불필요).

실제 Claude API 호출은 단위 테스트하지 않고, API 키가 없을 때의 방어
로직과 결과 파싱(from_dict), 구조화 출력 스키마의 정합성만 검증한다.
"""
import pytest

from stocksystem.analysis import chart_reader as cr


def test_label_sets():
    assert cr.SIGNAL_LABELS == ["적극매수", "매수", "중립", "매도", "적극매도"]
    assert "피벗 돌파 매수" in cr.ACTION_LABELS
    assert "추격 금지" in cr.ACTION_LABELS
    assert "2단계 상승국면" in cr.STAGE_LABELS


def test_api_key_available(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert cr.api_key_available() is False
    assert cr.api_key_available("sk-xyz") is True
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env")
    assert cr.api_key_available() is True


def test_read_chart_without_key_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(cr.ChartReaderError):
        cr.read_chart(b"not-an-image", api_key=None)


def test_from_dict_full():
    data = {
        "is_chart": True,
        "stage": "2단계 상승국면",
        "stage_reason": "주가가 200일선 위에서 우상향",
        "trend_template": [
            {"criterion": "주가 > 50 > 150 > 200일선", "status": "충족",
             "note": "정배열 확인"},
            {"criterion": "ROE 17% 이상", "status": "불명확",
             "note": "차트로 확인 불가"},
        ],
        "trend_template_summary": "확인 가능한 4개 중 3개 충족",
        "vcp_detected": True,
        "vcp_contractions": [
            {"label": "T1", "depth": "약 -24%", "note": "1차 수축"},
            {"label": "T2", "depth": "약 -11%", "note": "절반으로 축소"},
            {"label": "T3", "depth": "약 -4%", "note": "수렴 마디"},
        ],
        "volume_dry_up": "뚜렷함",
        "pivot_point": "308 부근",
        "vcp_note": "3차 수축으로 매물 소진",
        "action": "피벗 돌파 매수",
        "entry_pivot": "308 대량 거래량 돌파 시",
        "stop_loss": "약 -6% (285 부근)",
        "target": "380 부근",
        "risk_reward": "약 2.5:1",
        "support_levels": ["285 부근"],
        "resistance_levels": ["308 부근"],
        "key_observations": ["거래량 감소", "정배열"],
        "bullish_scenario": "피벗 돌파 시 상승",
        "bearish_scenario": "285 이탈 시 실패",
        "risks": ["시장 변동성"],
        "signal": "매수",
        "confidence": 72,
        "summary": "전형적 VCP 셋업.",
    }
    r = cr.ChartReading.from_dict(data)
    assert r.is_chart is True
    assert r.stage == "2단계 상승국면"
    assert r.action == "피벗 돌파 매수"
    assert r.vcp_detected is True
    assert len(r.vcp_contractions) == 3
    assert r.vcp_contractions[1]["depth"] == "약 -11%"
    assert r.volume_dry_up == "뚜렷함"
    assert r.signal == "매수"
    assert r.confidence == 72
    assert r.model == cr.DEFAULT_MODEL


def test_from_dict_defaults_on_missing():
    r = cr.ChartReading.from_dict({})
    assert r.signal == "중립"
    assert r.action == "회피"
    assert r.stage == "불명확"
    assert r.confidence == 0
    assert r.vcp_detected is False
    assert r.vcp_contractions == []
    assert r.trend_template == []
    assert r.is_chart is True


def test_schema_objects_are_strict():
    # 구조화 출력 스키마는 모든 object 에 additionalProperties:false 가 있어야 한다
    def check(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node.get("additionalProperties") is False
            for v in node.values():
                check(v)
        elif isinstance(node, list):
            for v in node:
                check(v)
    check(cr._SCHEMA)


def test_schema_required_matches_properties():
    # required 목록과 properties 키가 일치해야 한다 (strict 구조화 출력 요건)
    props = set(cr._SCHEMA["properties"].keys())
    required = set(cr._SCHEMA["required"])
    assert props == required


def test_enums_match_label_constants():
    props = cr._SCHEMA["properties"]
    assert props["signal"]["enum"] == cr.SIGNAL_LABELS
    assert props["action"]["enum"] == cr.ACTION_LABELS
    assert props["stage"]["enum"] == cr.STAGE_LABELS
