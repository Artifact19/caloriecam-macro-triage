@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" ( echo Run setup.bat first. & exit /b 1 )
set "VIRTUAL_ENV=%~dp0.venv"
set "PATH=%~dp0.venv\Scripts;%PATH%"
.venv\Scripts\python.exe scripts\validate_artifacts.py --warn-only
cd backend
echo.
echo Backend: http://127.0.0.1:8000  (API docs: http://127.0.0.1:8000/docs)
"%~dp0.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
