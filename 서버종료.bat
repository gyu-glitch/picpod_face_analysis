@echo off
rem stop background face-analysis server (kill port 8123 listener)
title stop face-analysis server
for /f "tokens=5" %%P in ('netstat -ano ^| findstr :8123 ^| findstr LISTENING') do (
  taskkill /f /pid %%P >nul 2>nul && echo Server stopped: PID %%P
)
pause
