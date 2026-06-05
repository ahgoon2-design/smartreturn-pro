@echo off
setlocal

cd /d "%~dp0.."

if not exist "backend\.venv\Scripts\python.exe" (
  echo backend\.venv\Scripts\python.exe not found.
  echo backend virtual environment must be prepared first.
  exit /b 1
)

cd /d "%~dp0..\backend"

echo SmartReturn Pro backend dev server
echo URL: http://127.0.0.1:8000
echo Health: http://127.0.0.1:8000/health
echo Stop: Ctrl+C

".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
