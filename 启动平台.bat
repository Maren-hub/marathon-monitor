@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo The project has not been installed yet.
  echo Please double-click 首次安装.bat first.
  pause
  exit /b 1
)

start "Marathon Backend" powershell -NoExit -ExecutionPolicy Bypass -File ".\scripts\start-backend.ps1"
start "Marathon Frontend" powershell -NoExit -ExecutionPolicy Bypass -File ".\scripts\start-frontend.ps1"
timeout /t 6 /nobreak >nul
start "" "http://127.0.0.1:5173"
