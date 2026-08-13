@echo off
rem ============================================================
rem  Allow inbound TCP 8123 for LAN clients  (RUN AS ADMIN, once)
rem  Right-click this file -> "Run as administrator"
rem ============================================================
net session >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Administrator rights required.
  echo         Right-click this file and choose "Run as administrator".
  pause & exit /b 1
)
netsh advfirewall firewall show rule name="PicPod face-analysis 8123" >nul 2>nul
if not errorlevel 1 (
  echo Rule already exists. Nothing to do.
  pause & exit /b 0
)
netsh advfirewall firewall add rule name="PicPod face-analysis 8123" dir=in action=allow protocol=TCP localport=8123
echo Done. Port 8123 is now reachable from the LAN.
pause
