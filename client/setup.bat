@echo off
rem ============================================================
rem  PicPod face-analysis client setup (LAN client PC)
rem  - installs Python + requests
rem  - asks server IP / target folder -> writes config.json
rem  - desktop shortcuts: [receiver] + [web GUI]
rem ============================================================
title face-analysis client setup
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo ============================================================
echo   PicPod face-analysis client setup
echo ============================================================
echo.

rem ---------- 1. Python ----------
echo [1/4] Checking Python...
where python >nul 2>nul
if errorlevel 1 (
  where winget >nul 2>nul
  if errorlevel 1 (
    echo [ERROR] Python and winget missing. Install Python 3.12 manually and rerun.
    pause & exit /b 1
  )
  echo       Installing Python...
  winget install -e --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
  echo.
  echo       Python installed. Close this window and RUN AGAIN.
  pause & exit /b 0
)
echo       OK

rem ---------- 2. Packages ----------
echo [2/4] Installing packages...
python -m pip install --upgrade pip --quiet
python -m pip install --upgrade requests --quiet
echo       OK

rem ---------- 3. Config ----------
echo [3/4] Config
if exist config.json (
  echo       config.json already exists - keeping it.
) else (
  set TARGET_ESC=%~dp0readings
  set TARGET_ESC=!TARGET_ESC:\=/!
  > config.json echo { "server": "http://100.88.205.178:8123", "target_dir": "!TARGET_ESC!", "poll_interval": 2, "flatten": false }
  echo       Default config written. Edit config.json to change server/folder.
)
echo       OK

rem ---------- 4. Shortcuts ----------
echo [4/4] Creating desktop shortcuts...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$w=New-Object -ComObject WScript.Shell;" ^
  "$d=[Environment]::GetFolderPath('Desktop');" ^
  "$u=$w.SpecialFolders('Startup');" ^
  "$cfg=Get-Content '%~dp0config.json' -Raw | ConvertFrom-Json;" ^
  "$s=$w.CreateShortcut((Join-Path $d 'PicPod Result Receiver.lnk'));" ^
  "$s.TargetPath='%~dp0수신기실행.bat'; $s.WorkingDirectory='%~dp0'; $s.Save();" ^
  "$s=$w.CreateShortcut((Join-Path $u 'PicPod Result Receiver.lnk'));" ^
  "$s.TargetPath='%~dp0수신기실행.bat'; $s.WorkingDirectory='%~dp0'; $s.Save();" ^
  "$s=$w.CreateShortcut((Join-Path $d 'PicPod Analysis GUI.url'));" ^
  "$s.TargetPath=$cfg.server; $s.Save()"
echo       OK

echo.
echo ============================================================
echo   Done.
echo   - [PicPod Result Receiver] : auto-download results (autostart)
echo   - [PicPod Analysis GUI]    : open analysis page in browser
echo ============================================================
pause
