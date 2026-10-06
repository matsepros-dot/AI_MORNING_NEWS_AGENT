@echo off
setlocal
cd /d "%~dp0"
if not exist logs mkdir logs
set "PYTHONUTF8=1"
set "AGENT_PYTHON=python"
if exist ".venv\Scripts\python.exe" set "AGENT_PYTHON=%~dp0.venv\Scripts\python.exe"
"%AGENT_PYTHON%" "%~dp0src\main.py" %*
set "AGENT_EXIT=%errorlevel%"
echo [%date% %time%] RUN exit=%AGENT_EXIT% >>logs\launcher.log
if "%AGENT_EXIT%"=="0" (echo [PASS] RUN_AGENT.cmd) else (echo [PARTIAL/FAIL] RUN_AGENT.cmd exit=%AGENT_EXIT% - see logs\agent.log)
exit /b %AGENT_EXIT%
