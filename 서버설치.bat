@echo off
rem ============================================================
rem  PicPod face-analysis SERVER setup (analysis PC)
rem  Run once after cloning the repo. Installs Python venv,
rem  Ollama + EXAONE model, face landmark model, shortcuts.
rem ============================================================
title face-analysis server setup
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo ============================================================
echo   PicPod face-analysis SERVER setup
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
echo [1/6] Checking Python...
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
echo [2/6] Creating venv and installing packages (a few minutes)...
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
echo [3/6] Checking Ollama...
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
echo [4/6] Language model
echo       [1] exaone3.5:7.8b  - better quality, needs ~6GB VRAM (recommended w/ GPU)
echo       [2] exaone3.5:2.4b  - lighter, ~2.5GB VRAM
echo       [3] both
choice /c 123 /n /m "      Select (1/2/3): "
if errorlevel 3 ( set MODELS=exaone3.5:7.8b exaone3.5:2.4b
) else if errorlevel 2 ( set MODELS=exaone3.5:2.4b
) else set MODELS=exaone3.5:7.8b
for %%M in (!MODELS!) do (
  echo       Downloading %%M ...
  "%OLLAMA_EXE%" pull %%M
)
echo       OK

rem ---------- 5. Face landmark model ----------
echo [5/6] Downloading face landmark model...
if not exist models mkdir models
if not exist models\face_landmarker.task (
  curl -L -s -o models\face_landmarker.task https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
)
echo       OK

rem ---------- 6. Shortcut ----------
echo [6/6] Creating desktop shortcut...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$w=New-Object -ComObject WScript.Shell;" ^
  "$d=[Environment]::GetFolderPath('Desktop');" ^
  "$s=$w.CreateShortcut((Join-Path $d 'PicPod Analysis Server.lnk'));" ^
  "$s.TargetPath='%~dp0서버실행.bat'; $s.WorkingDirectory='%~dp0'; $s.Save()"
echo       OK

echo.
echo ============================================================
echo   Done.
echo   1. Right-click [방화벽허용.bat] -^> Run as administrator  (once)
echo   2. Double-click [PicPod Analysis Server] on the Desktop
echo.
echo   This PC's address for clients:
ipconfig | findstr /c:"IPv4"
echo   Clients connect to  http://^<that address^>:8123
echo ============================================================
pause
