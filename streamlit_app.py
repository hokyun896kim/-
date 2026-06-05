"""Streamlit Community Cloud / 웹 배포용 진입점.

실제 대시보드 코드는 stocksystem/app/dashboard.py 에 있다.
Streamlit Cloud 는 기본적으로 루트의 streamlit_app.py 를 찾으므로,
이 파일을 두면 별도 설정 없이 바로 배포된다.

매 rerun 마다 대시보드 스크립트를 새로 실행해야 하므로 import 가 아니라
runpy 로 실행한다(모듈 캐시로 인한 반응성 손실 방지).
"""
import runpy
from pathlib import Path

_APP = Path(__file__).resolve().parent / "stocksystem" / "app" / "dashboard.py"
runpy.run_path(str(_APP), run_name="__main__")
