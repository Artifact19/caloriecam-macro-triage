@echo off
setlocal
cd /d "%~dp0frontend"
if not exist node_modules ( call npm ci )
node ./node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173
