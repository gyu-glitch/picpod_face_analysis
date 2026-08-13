@echo off
title PicPod result receiver
cd /d "%~dp0"
chcp 65001 >nul
python 결과수신기.py
pause
