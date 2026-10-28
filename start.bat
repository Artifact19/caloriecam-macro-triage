@echo off
rem ===== Single-command launcher: starts backend + frontend and opens the browser =====
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [start] First run detected - running setup.bat ...
  call setup.bat || exit /b 1
)
if not exist "frontend\node_modules" (
  echo [start] Installing frontend dependencies ...
  pushd frontend
  call npm ci
  popd
)

echo [start] Launching backend  on http://127.0.0.1:8000
start "Meal Triage - Backend" cmd /k call run_backend.bat
echo [start] Launching frontend on http://127.0.0.1:5173
start "Meal Triage - Frontend" cmd /k call run_frontend.bat

rem Give the dev servers a few seconds, then open the UI.
timeout /t 5 /nobreak >nul
start "" http://127.0.0.1:5173
echo [start] Both servers launched. Close the two server windows to stop the app.
exit /b 0
