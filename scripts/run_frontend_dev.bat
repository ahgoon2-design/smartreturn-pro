@echo off
setlocal

cd /d "%~dp0..\frontend"

echo SmartReturn Pro frontend dev server
echo URL: http://127.0.0.1:5173/login
echo Stop: Ctrl+C

npm.cmd run dev -- --host 127.0.0.1
