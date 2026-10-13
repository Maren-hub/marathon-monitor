@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File ".\scripts\setup.ps1"
echo.
echo Setup finished. You can now double-click 启动平台.bat.
pause
