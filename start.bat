@echo off
rem ============================================
rem  Data Entry Agent - 一键启动（前端 + 后端）
rem ============================================
chcp 65001 >nul
setlocal

echo [1/2] 启动后端 (FastAPI :8000) ...
start "DataEntry-Backend" cmd /k "cd /d %~dp0backend && set HTTP_PROXY= && set HTTPS_PROXY= && C:\Users\denglw\.workbuddy\binaries\python\envs\data_entry\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo [2/2] 启动前端 (Vite :5174) ...
start "DataEntry-Frontend" cmd /k "cd /d %~dp0frontend && set HTTP_PROXY= && set HTTPS_PROXY= && C:\Users\denglw\.workbuddy\binaries\node\versions\22.22.2\node.exe node_modules\vite\bin\vite.js --port 5174 --strictPort --host 127.0.0.1"

echo.
echo 前端访问: http://127.0.0.1:5174
echo 后端接口: http://127.0.0.1:8000
echo.
endlocal
