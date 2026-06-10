@echo off
rem morning-brief agent - manual/scheduled entry point (Windows adapter rules V3.5)
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
pushd "%~dp0"
echo [morning-brief] running...
python brief.py
if errorlevel 1 (
  echo [ERROR] run failed - see error.log
  ping -n 6 127.0.0.1 > nul
  popd
  exit /b 1
)
echo [OK] report saved under reports\
ping -n 4 127.0.0.1 > nul
popd
exit /b 0
