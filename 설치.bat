@echo off
rem ============================================================
rem  PicPod face-analysis setup
rem  Installs everything needed to use the pipeline as a module:
rem    Python venv + packages, Ollama + EXAONE model, face model
rem  Usage: just double-click.  (optional: setup.bat 7.8b|2.4b|both)
rem ============================================================
title face-analysis setup
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo ============================================================
echo   PicPod face-analysis setup
echo ============================================================
echo.

rem ---------- 0. winget ----------
where winget >nul 2>nul
if errorlevel 1 (
  echo [ERROR] winget not found. Install "App Installer" from Microsoft Store,
  echo         then run this again.
  pause & exit /b 1
)

rem ---------- 1. Python ----------
echo [1/5] Checking Python...
where python >nul 2>nul
if errorlevel 1 (
  echo       Installing Python 3.12...
  winget install -e --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
  echo.
  echo       Python installed. Close this window and RUN AGAIN.
  pause & exit /b 0
)
echo       OK

rem ---------- 2. venv + packages ----------
echo [2/5] Creating venv and installing packages (a few minutes)...
if not exist .venv (
  python -m venv .venv
)
.venv\Scripts\python.exe -m pip install --upgrade pip --quiet
.venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
if errorlevel 1 (
  echo [ERROR] pip install failed. Check network.
  pause & exit /b 1
)
echo       OK

rem ---------- 3. Ollama ----------
echo [3/5] Checking Ollama...
set OLLAMA_EXE=%LOCALAPPDATA%\Programs\Ollama\ollama.exe
if not exist "%OLLAMA_EXE%" (
  echo       Installing Ollama...
  winget install -e --id Ollama.Ollama --silent --accept-package-agreements --accept-source-agreements
)
if not exist "%OLLAMA_EXE%" (
  echo [ERROR] Ollama install failed. Install manually from https://ollama.com
  pause & exit /b 1
)
curl -s -o nul -m 2 http://127.0.0.1:11434/api/tags
if errorlevel 1 (
  echo       Starting Ollama...
  start "" /min "%OLLAMA_EXE%" serve
  timeout /t 5 /nobreak >nul
)
echo       OK

rem ---------- 4. LLM model ----------
echo [4/5] Language model
set PICK=%1
if "%PICK%"=="" (
  echo       [1] exaone3.5:7.8b  - better quality, ~6GB VRAM, recommended w/ GPU
  echo       [2] exaone3.5:2.4b  - lighter, ~2.5GB VRAM
  echo       [3] both
  choice /c 123 /n /m "      Select (1/2/3): "
  if errorlevel 3 ( set PICK=both
  ) else if errorlevel 2 ( set PICK=2.4b
  ) else set PICK=7.8b
)
if /i "%PICK%"=="both" ( set MODELS=exaone3.5:7.8b exaone3.5:2.4b
) else if /i "%PICK%"=="2.4b" ( set MODELS=exaone3.5:2.4b
) else set MODELS=exaone3.5:7.8b
for %%M in (!MODELS!) do (
  echo       Downloading %%M ...
  "%OLLAMA_EXE%" pull %%M
)
echo       OK

rem ---------- 5. Face landmark model ----------
echo [5/5] Downloading face landmark model...
if not exist models mkdir models
if not exist models\face_landmarker.task (
  curl -L -s -o models\face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
)
echo       OK

echo.
echo ============================================================
echo   Done. Use it from your own code:
echo.
echo     from app.api import analyze_photo
echo     result = analyze_photo("face.jpg", personas=["kind"])
echo.
echo   Details: README.md  (module usage, tuning points)
echo.
echo   Optional HTTP server (only if you want the web GUI / LAN API):
echo     run 서버실행.bat, and for LAN access run 방화벽허용.bat as admin
echo ============================================================
pause
