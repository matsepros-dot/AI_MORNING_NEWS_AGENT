@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "AGENT_PYTHON=python"
if exist ".venv\Scripts\python.exe" set "AGENT_PYTHON=%~dp0.venv\Scripts\python.exe"
echo Complete GitHub sign-in in the official Git Credential Manager browser flow.
"%AGENT_PYTHON%" src\runtime.py --login
if errorlevel 1 goto fail
call RUN_AGENT.cmd
exit /b %errorlevel%
:fail
echo [FAIL] GitHub sign-in was not completed. No password or token is stored in this project.
pause
exit /b 1
