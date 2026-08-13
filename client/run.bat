@echo off
title PicPod result receiver
cd /d "%~dp0"
if not exist result mkdir result
chcp 65001 >nul
python receiver.py
pause
