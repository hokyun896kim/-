#!/usr/bin/env python3
"""터미널용 AI 비서.

사용 예:
  python assistant_cli.py                        # 대화 모드
  python assistant_cli.py "엔비디아 어때?"        # 한 번만 묻고 종료
  python assistant_cli.py --provider sample      # 오프라인 데모 데이터
  python assistant_cli.py --engine rules         # LLM 없이 규칙 엔진만

ANTHROPIC_API_KEY 가 설정돼 있으면 Claude 로 자유 대화가 되고, 없으면
키워드 기반 규칙 엔진으로 내려간다(둘 다 같은 분석 모듈을 호출한다).
"""
from __future__ import annotations

import argparse
import sys

from stocksystem.assistant import Assistant
from stocksystem.config import load_config

BANNER = """
╭──────────────────────────────────────────────────────────╮
│  🤖 미국주식 분석 비서                                   │
│  자연어로 물어보세요. 종료: exit / quit / q · 새 대화: new │
╰──────────────────────────────────────────────────────────╯"""


def _print_reply(reply, *, show_tools: bool) -> None:
    if show_tools and reply.tool_calls:
        names = ", ".join(f"{c.name}({', '.join(map(str, c.args.values()))})"
                          if c.args else c.name for c in reply.tool_calls)
        print(f"\n\033[2m› 실행한 도구: {names}\033[0m")
    print(f"\n{reply.text}")
    if reply.note:
        print(f"\n\033[2m※ {reply.note}\033[0m")


def main() -> None:
    parser = argparse.ArgumentParser(description="미국주식 AI 비서")
    parser.add_argument("question", nargs="*", help="질문 (생략하면 대화 모드)")
    parser.add_argument("--provider", help="데이터 소스 (yahoo/sample)")
    parser.add_argument("--engine", choices=["auto", "claude", "rules"],
                        help="엔진 선택 (기본: config 의 assistant.engine)")
    parser.add_argument("--model", help="Claude 모델 ID 재정의")
    parser.add_argument("--quiet", action="store_true",
                        help="어떤 도구를 썼는지 표시하지 않음")
    args = parser.parse_args()

    cfg = load_config()
    bot = Assistant(cfg,
                    provider_name=args.provider or cfg.data_provider,
                    engine=args.engine or cfg.assistant.engine,
                    model=args.model)

    engine_desc = ("Claude (자유 대화)" if bot.engine == "claude"
                   else "규칙 기반 (ANTHROPIC_API_KEY 없음 → 키워드 매칭)")

    if args.question:
        _print_reply(bot.ask(" ".join(args.question)),
                     show_tools=not args.quiet)
        return

    print(BANNER)
    print(f"엔진: {engine_desc} · 데이터: {bot.ctx.provider_name}")
    print("예시: " + " / ".join(Assistant.examples()[:4]))

    while True:
        try:
            q = input("\n\033[1m나 ›\033[0m ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n안녕히 가세요.")
            return
        if q.lower() in {"exit", "quit", "q", "종료"}:
            print("안녕히 가세요.")
            return
        if q.lower() in {"new", "reset", "새 대화"}:
            bot.reset()
            print("\033[2m대화 기록을 지웠습니다.\033[0m")
            continue
        if not q:
            continue
        try:
            _print_reply(bot.ask(q), show_tools=not args.quiet)
        except KeyboardInterrupt:
            print("\n(중단됨)")
        except Exception as e:                # 한 번의 실패로 세션이 죽지 않게
            print(f"\n오류가 났습니다: {type(e).__name__}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
