@echo off
rem One-shot environment setup (Windows).
rem   setup.bat           -> CPU-only PyTorch (smaller, enough for serving)
rem   setup.bat --cuda    -> CUDA 12.4 PyTorch (recommended for training notebook 02 on an NVIDIA GPU)
setlocal
cd /d "%~dp0"
set "USE_CUDA=0"
if /i "%~1"=="--cuda" set "USE_CUDA=1"

if not exist ".venv\Scripts\python.exe" ( python -m venv .venv || goto :err )
set "VIRTUAL_ENV=%~dp0.venv"
set "PATH=%~dp0.venv\Scripts;%PATH%"

.venv\Scripts\python.exe -m pip install --upgrade pip

if "%USE_CUDA%"=="1" (
  .venv\Scripts\pip.exe install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu124 || goto :err
) else (
  .venv\Scripts\pip.exe install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cpu || goto :err
)
.venv\Scripts\pip.exe install -r backend\requirements.txt || goto :err
.venv\Scripts\pip.exe install -r notebooks\requirements-notebooks.txt || goto :err
.venv\Scripts\python.exe -m ipykernel install --user --name python3 --display-name "Python 3 (meal-triage)" >nul 2>&1

pushd frontend
if exist package-lock.json ( call npm ci || goto :err ) else ( call npm install || goto :err )
popd

if not exist .env if exist .env.example copy /y .env.example .env >nul
echo.
echo Setup complete. Next: run notebooks (python scripts\run_notebooks.py), then start.bat
exit /b 0
:err
echo Setup failed. See messages above.
exit /b 1
