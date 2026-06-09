"""차트 이미지 판독 엔진 (Claude 비전 모델 · 미너비니 SEPA/VCP 기반).

업로드한 차트 캡처 이미지를 Claude 비전 모델에게 보내, 마크 미너비니의
SEPA(Specific Entry Point Analysis)와 VCP(Volatility Contraction Pattern)
관점으로 판독한다.

판독 골자:
- 트렌드 템플릿 (주가 > 50 > 150 > 200일선, 200일선 우상향, 52주 고저 위치 등)
- 스테이지 분석 (2단계 상승국면 매집 신호 포착)
- VCP 변동성 수축 (3~4차 수축, 각 단계가 이전의 ~절반, 거래량 감소)
- 피벗 포인트 + 손절/목표/손익비 제안 (5% 추격 금지 규율 반영)

설계 노트:
- `anthropic` 패키지는 함수 안에서 지연 import 한다. 패키지가 없거나
  네트워크가 없는 환경(오프라인 데모)에서도 stocksystem 의 나머지 기능과
  테스트가 영향을 받지 않도록 하기 위함이다.
- 비전 + 구조화 출력(json_schema)을 사용해 항상 파싱 가능한 결과를 받는다.
- 모델은 기본적으로 가장 똑똑한 claude-opus-4-8 을 적응형 사고와 함께 쓴다.

⚠️ 결과는 교육·연구용 참고 자료이며 투자자문이 아니다.
"""
from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from typing import Optional

# 기본 모델: 가장 capable 한 Opus 4.8
DEFAULT_MODEL = "claude-opus-4-8"

# 매매 신호 등급(스코어링 모듈과 톤을 맞춘다)
SIGNAL_LABELS = ["적극매수", "매수", "중립", "매도", "적극매도"]

# 미너비니 관점의 행동 권고
ACTION_LABELS = [
    "피벗 돌파 매수",      # 피벗을 대량 거래량과 함께 막 돌파
    "관찰 대기",           # VCP/베이스 형성 중, 피벗 돌파 전
    "추격 금지",           # 이미 피벗 +5% 이상 확장 — 신규 진입 부적합
    "회피",                # 셋업(트렌드 템플릿/스테이지) 미충족
]

# 와인스타인 스테이지
STAGE_LABELS = [
    "1단계 바닥권", "2단계 상승국면", "3단계 천장권", "4단계 하락국면", "불명확",
]

_STATUS = ["충족", "미충족", "불명확"]
_DRYUP = ["뚜렷함", "부분적", "없음", "불명확"]

# 차트 판독 전문가 시스템 프롬프트 (미너비니 SEPA/VCP)
_SYSTEM = """\
당신은 마크 미너비니(Mark Minervini)의 SEPA·VCP 매매법을 20년간 운용해 온
미국 성장주 전문 테크니컬 트레이더입니다. 사용자가 올린 '주가 차트 이미지'를
미너비니 프레임워크로 정밀 판독합니다.

[판독 원칙]
- 이미지에 실제로 보이는 것만 근거로 삼습니다. 보이지 않는 가격·날짜·재무
  수치는 지어내지 마세요. 축 눈금이 안 보이면 '대략/상단 부근'처럼 상대적으로
  표현하고, 해당 항목 status 는 '불명확'으로 둡니다.
- 모든 설명은 한국어로, 초보자도 이해할 수 있게 풀어서 씁니다.
- 이것은 교육용 분석이며 투자 권유가 아닙니다.

[1. 스테이지 분석] 와인스타인 4단계 중 어디인지 판정합니다.
  1단계(바닥 횡보) → 2단계(상승) → 3단계(천장) → 4단계(하락).
  미너비니는 오직 '2단계 상승국면'의 주도주만 매수 대상으로 삼습니다.

[2. 트렌드 템플릿] 이미지에서 확인 가능한 항목을 점검합니다.
  - 주가가 50일선 위 / 50일선 > 150일선 > 200일선 정배열인가
  - 200일(또는 장기) 이동평균선이 우상향하는가
  - 현재가가 52주 신저가 대비 +30% 이상, 신고가 대비 -25% 이내인가
  - 상대강도(차트상 강세 흐름)가 시장을 앞서는가
  ※ 재무(EPS/매출/ROE/기관지분)는 차트 이미지만으로는 확인 불가 →
     보이지 않으면 status '불명확'으로 두고 추정하지 마세요.

[3. VCP 변동성 수축] 베이스(횡보) 안에서 되돌림 폭이 점점 줄어드는지 봅니다.
  - 통상 3~4차 수축(T1→T2→T3…). 각 조정폭은 직전의 대략 절반으로 수렴
    (예: -20% → -10% → -5% → -2%). 보이는 대로 각 수축폭을 추정합니다.
  - 거래량 감소(Volume Dry-Up): 수축 후반·조정 구간에서 거래량이 평소의
    40~60% 이하로 바싹 마르면 매도 물량 소진의 강한 신호입니다.
  - 피벗 포인트: 가격·거래량이 한 점으로 수렴한 마지막 마디의 돌파 기준선.

[4. 진입·리스크 규율]
  - 매수는 피벗을 '대량 거래량'과 함께 돌파할 때만. 손절은 통상 -7~8%,
    타이트한 VCP(수축 꼬리 3~5%)는 -5~6%로 더 좁힙니다.
  - 손익비는 최소 2:1(이상적 3:1) 이상이어야 합니다.
  - 피벗을 이미 +5% 이상 벗어나 확장된 상태면 추격 매수 금지(action='추격 금지').
  - 셋업이 트렌드 템플릿/스테이지에 부합하지 않으면 action='회피'.

이미지가 주가 차트가 아니거나 흐려 판독이 어려우면 is_chart=false, signal='중립',
confidence 를 낮게 두고 summary 에 그 사실을 적습니다.
"""

# 구조화 출력 스키마 (numeric min/max 등 미지원 제약은 쓰지 않는다)
_SCHEMA = {
    "type": "object",
    "properties": {
        "is_chart": {
            "type": "boolean",
            "description": "이미지가 판독 가능한 주가 차트이면 true",
        },
        "stage": {
            "type": "string",
            "enum": STAGE_LABELS,
            "description": "와인스타인 스테이지 판정",
        },
        "stage_reason": {
            "type": "string",
            "description": "스테이지 판정 근거 1~3문장",
        },
        "trend_template": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "criterion": {"type": "string", "description": "점검 항목"},
                    "status": {"type": "string", "enum": _STATUS},
                    "note": {"type": "string", "description": "근거/관찰"},
                },
                "required": ["criterion", "status", "note"],
                "additionalProperties": False,
            },
            "description": "트렌드 템플릿 항목별 점검 결과",
        },
        "trend_template_summary": {
            "type": "string",
            "description": "예: '확인 가능한 6개 중 5개 충족'",
        },
        "vcp_detected": {
            "type": "boolean",
            "description": "VCP(변동성 수축 패턴)가 식별되면 true",
        },
        "vcp_contractions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string", "description": "T1, T2 등"},
                    "depth": {"type": "string",
                              "description": "조정폭 추정 (예: 약 -12%)"},
                    "note": {"type": "string"},
                },
                "required": ["label", "depth", "note"],
                "additionalProperties": False,
            },
            "description": "수축 단계별 되돌림 폭 (없으면 빈 배열)",
        },
        "volume_dry_up": {
            "type": "string",
            "enum": _DRYUP,
            "description": "거래량 감소(Volume Dry-Up) 정도",
        },
        "pivot_point": {
            "type": "string",
            "description": "피벗 포인트(돌파 기준선). 보이는 대로 묘사",
        },
        "vcp_note": {
            "type": "string",
            "description": "VCP 종합 해설 2~4문장",
        },
        "action": {
            "type": "string",
            "enum": ACTION_LABELS,
            "description": "미너비니 관점의 행동 권고",
        },
        "entry_pivot": {
            "type": "string",
            "description": "진입 기준(피벗 돌파) 설명",
        },
        "stop_loss": {
            "type": "string",
            "description": "손절 기준 (가격대 또는 % 폭)",
        },
        "target": {
            "type": "string",
            "description": "1차 목표 구간",
        },
        "risk_reward": {
            "type": "string",
            "description": "예상 손익비 (예: 약 2.5:1)",
        },
        "support_levels": {
            "type": "array",
            "items": {"type": "string"},
            "description": "지지 구간 (보이는 대로)",
        },
        "resistance_levels": {
            "type": "array",
            "items": {"type": "string"},
            "description": "저항 구간 (보이는 대로)",
        },
        "key_observations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "핵심 관찰 포인트 3~6개",
        },
        "bullish_scenario": {
            "type": "string",
            "description": "상방(피벗 돌파) 시나리오",
        },
        "bearish_scenario": {
            "type": "string",
            "description": "하방(베이스 실패) 시나리오",
        },
        "risks": {
            "type": "array",
            "items": {"type": "string"},
            "description": "유의해야 할 리스크",
        },
        "signal": {
            "type": "string",
            "enum": SIGNAL_LABELS,
            "description": "종합 매매 신호",
        },
        "confidence": {
            "type": "integer",
            "description": "판독 확신도 0~100",
        },
        "summary": {
            "type": "string",
            "description": "전체 판독 요약 (3~5문장)",
        },
    },
    "required": [
        "is_chart", "stage", "stage_reason", "trend_template",
        "trend_template_summary", "vcp_detected", "vcp_contractions",
        "volume_dry_up", "pivot_point", "vcp_note", "action", "entry_pivot",
        "stop_loss", "target", "risk_reward", "support_levels",
        "resistance_levels", "key_observations", "bullish_scenario",
        "bearish_scenario", "risks", "signal", "confidence", "summary",
    ],
    "additionalProperties": False,
}


@dataclass
class ChartReading:
    """차트 판독 결과 (미너비니 SEPA/VCP)."""
    is_chart: bool
    stage: str
    stage_reason: str
    trend_template: list[dict]
    trend_template_summary: str
    vcp_detected: bool
    vcp_contractions: list[dict]
    volume_dry_up: str
    pivot_point: str
    vcp_note: str
    action: str
    entry_pivot: str
    stop_loss: str
    target: str
    risk_reward: str
    support_levels: list[str]
    resistance_levels: list[str]
    key_observations: list[str]
    bullish_scenario: str
    bearish_scenario: str
    risks: list[str]
    signal: str
    confidence: int
    summary: str
    model: str = DEFAULT_MODEL

    @classmethod
    def from_dict(cls, d: dict, model: str = DEFAULT_MODEL) -> "ChartReading":
        return cls(
            is_chart=bool(d.get("is_chart", True)),
            stage=d.get("stage", "불명확"),
            stage_reason=d.get("stage_reason", ""),
            trend_template=list(d.get("trend_template", [])),
            trend_template_summary=d.get("trend_template_summary", ""),
            vcp_detected=bool(d.get("vcp_detected", False)),
            vcp_contractions=list(d.get("vcp_contractions", [])),
            volume_dry_up=d.get("volume_dry_up", "불명확"),
            pivot_point=d.get("pivot_point", ""),
            vcp_note=d.get("vcp_note", ""),
            action=d.get("action", "회피"),
            entry_pivot=d.get("entry_pivot", ""),
            stop_loss=d.get("stop_loss", ""),
            target=d.get("target", ""),
            risk_reward=d.get("risk_reward", ""),
            support_levels=list(d.get("support_levels", [])),
            resistance_levels=list(d.get("resistance_levels", [])),
            key_observations=list(d.get("key_observations", [])),
            bullish_scenario=d.get("bullish_scenario", ""),
            bearish_scenario=d.get("bearish_scenario", ""),
            risks=list(d.get("risks", [])),
            signal=d.get("signal", "중립"),
            confidence=int(d.get("confidence", 0)),
            summary=d.get("summary", ""),
            model=model,
        )


class ChartReaderError(RuntimeError):
    """차트 판독 중 발생한 오류 (API 키 누락, 패키지 미설치 등)."""


def api_key_available(api_key: Optional[str] = None) -> bool:
    """사용 가능한 Anthropic API 키가 있는지 확인."""
    return bool(api_key or os.environ.get("ANTHROPIC_API_KEY"))


def read_chart(
    image_bytes: bytes,
    media_type: str = "image/png",
    *,
    context_note: str = "",
    api_key: Optional[str] = None,
    model: str = DEFAULT_MODEL,
) -> ChartReading:
    """차트 이미지를 미너비니 SEPA/VCP 관점으로 판독한다.

    Parameters
    ----------
    image_bytes : 차트 이미지 원본 바이트
    media_type  : "image/png" | "image/jpeg" | "image/webp" | "image/gif"
    context_note: 종목/기간 등 사용자가 덧붙이는 맥락 (선택)
    api_key     : 명시적 키. 없으면 ANTHROPIC_API_KEY 환경변수 사용
    model       : 사용할 Claude 모델 ID
    """
    try:
        import anthropic
    except ImportError as e:  # 패키지 미설치
        raise ChartReaderError(
            "anthropic 패키지가 설치되어 있지 않습니다. "
            "`pip install anthropic` 후 다시 시도하세요."
        ) from e

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ChartReaderError(
            "Anthropic API 키가 없습니다. 환경변수 ANTHROPIC_API_KEY 를 "
            "설정하거나 화면에서 키를 입력하세요."
        )

    client = anthropic.Anthropic(api_key=key)
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    prompt = ("이 주가 차트를 미너비니 SEPA·VCP 관점으로 판독해 주세요.")
    if context_note.strip():
        prompt += f"\n\n참고 맥락: {context_note.strip()}"

    try:
        response = client.messages.create(
            model=model,
            max_tokens=8192,
            system=_SYSTEM,
            thinking={"type": "adaptive"},
            output_config={
                "format": {"type": "json_schema", "schema": _SCHEMA}
            },
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }],
        )
    except anthropic.AuthenticationError as e:
        raise ChartReaderError("API 키가 유효하지 않습니다.") from e
    except anthropic.APIStatusError as e:
        raise ChartReaderError(f"API 오류({e.status_code}): {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise ChartReaderError("네트워크 연결 오류입니다.") from e

    # 구조화 출력: 첫 text 블록이 스키마를 만족하는 JSON
    import json
    text = next((b.text for b in response.content if b.type == "text"), "")
    if not text:
        raise ChartReaderError("모델이 빈 응답을 반환했습니다.")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ChartReaderError("응답을 JSON 으로 해석하지 못했습니다.") from e

    return ChartReading.from_dict(data, model=model)
