@echo off
setlocal

cd /d "%~dp0"

echo SmartReturn Pro frontend starting...
echo Root: %CD%

if not exist "frontend\package.json" (
  echo [ERROR] frontend\package.json not found.
  echo Run this file from the SmartReturn Pro repository root.
  pause
  exit /b 1
)

if not exist "frontend\node_modules" (
  echo [ERROR] frontend\node_modules not found.
  echo Run npm install in the frontend folder first.
  pause
  exit /b 1
)

cd frontend

if "%VITE_API_BASE_URL%"=="" (
  if not "%SMARTRETURN_BACKEND_PORT%"=="" (
    set "VITE_API_BASE_URL=http://127.0.0.1:%SMARTRETURN_BACKEND_PORT%"
  )
)

echo Frontend URL: http://127.0.0.1:5173
if not "%VITE_API_BASE_URL%"=="" (
  echo API Base URL: %VITE_API_BASE_URL%
)
echo Press Ctrl+C to stop the frontend dev server.
echo.

npm.cmd run dev -- --host 127.0.0.1

echo.
echo Frontend dev server stopped or failed to start.
pause
