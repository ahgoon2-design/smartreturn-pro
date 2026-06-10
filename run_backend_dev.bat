@echo off
setlocal

cd /d "%~dp0"

echo SmartReturn Pro backend starting...
echo Root: %CD%

if not exist "backend\app\main.py" (
  echo [ERROR] backend\app\main.py not found.
  echo Run this file from the SmartReturn Pro repository root.
  pause
  exit /b 1
)

cd backend

set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
  echo [WARN] backend\.venv\Scripts\python.exe not found. Falling back to python on PATH.
  set "PYTHON_EXE=python"
)

if "%SMARTRETURN_BACKEND_PORT%"=="" (
  set "SMARTRETURN_BACKEND_PORT=8000"
)

set "UVICORN_RELOAD="
if /I "%SMARTRETURN_BACKEND_RELOAD%"=="1" (
  set "UVICORN_RELOAD=--reload"
  echo Reload: enabled by SMARTRETURN_BACKEND_RELOAD=1
) else (
  echo Reload: disabled for stable local startup
)

echo Backend URL: http://127.0.0.1:%SMARTRETURN_BACKEND_PORT%
echo Health URL:  http://127.0.0.1:%SMARTRETURN_BACKEND_PORT%/health
echo Press Ctrl+C to stop the backend server.
echo.

"%PYTHON_EXE%" -m uvicorn app.main:app --host 127.0.0.1 --port %SMARTRETURN_BACKEND_PORT% %UVICORN_RELOAD%

echo.
echo Backend server stopped or failed to start.
pause
