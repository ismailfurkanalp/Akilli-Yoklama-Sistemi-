@echo off
chcp 65001 >nul
cd /d "%~dp0"
call .venv\Scripts\activate.bat
echo Kamera teshisi basliyor, kameraya bakin (yaklasik 30 sn)...
python kamera_teshis.py
pause
