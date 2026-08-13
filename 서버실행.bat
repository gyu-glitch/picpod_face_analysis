@echo off
rem ============================================================
rem  PicPod face-analysis server (GPU PC)
rem  Starts Ollama (if needed) + FastAPI on 0.0.0.0:8123
rem  LAN clients connect to  http://<this-pc-ip>:8123
rem ============================================================
title face-analysis server
setlocal
cd /d "%~dp0"

rem ---------- Ollama ----------
curl -s -o nul -m 2 http://127.0.0.1:11434/api/tags
if errorlevel 1 (
  echo Starting Ollama...
  start "" /min "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve
  timeout /t 4 /nobreak >nul
)

rem ---------- API server ----------
echo.
echo   Server starting on port 8123 (all interfaces)
echo   This PC IP:
ipconfig | findstr /c:"IPv4"
echo.
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8123
pause
