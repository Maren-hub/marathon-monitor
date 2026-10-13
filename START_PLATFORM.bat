@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo 正在检查智跑慧巡平台文件，请稍候……
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\prepare-portable.ps1"
if errorlevel 1 (
  echo.
  echo 检查失败，请把当前窗口截图发给项目负责人。
  pause
  exit /b 1
)

start "智跑慧巡 后端" powershell -NoExit -NoProfile -ExecutionPolicy Bypass -File ".\scripts\start-backend-portable.ps1"
start "智跑慧巡 前端" powershell -NoExit -NoProfile -ExecutionPolicy Bypass -File ".\scripts\start-frontend-portable.ps1"

echo 正在启动前端和后端……
timeout /t 10 /nobreak >nul
start "" "http://127.0.0.1:5173/"

echo.
echo 浏览器已经打开。使用期间请不要关闭刚出现的两个 PowerShell 窗口。
timeout /t 4 /nobreak >nul
