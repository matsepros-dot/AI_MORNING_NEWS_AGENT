@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>&1 || goto fail
python --version || goto fail
python src\runtime.py --configure || goto fail
if not exist ".venv\Scripts\python.exe" python -m venv .venv
if not exist ".venv\Scripts\python.exe" goto fail
".venv\Scripts\python.exe" -m pip install --upgrade pip || goto fail
".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto fail
".venv\Scripts\python.exe" -c "import requests,feedparser,bs4,dateutil,rapidfuzz,jinja2" || goto fail
echo [PASS] INSTALL.cmd
exit /b 0
:fail
if not exist logs mkdir logs
echo [%date% %time%] INSTALL FAIL>>logs\launcher.log
echo [FAIL] INSTALL.cmd - see logs\launcher.log
exit /b 1
