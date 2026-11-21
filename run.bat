@echo off
title Voxora Voice - Server
cd /d "%~dp0backend"
if not exist ".venv\Scripts\python.exe" (
  echo Please double-click setup.bat first.
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"
echo.
echo Voxora Voice is starting at http://localhost:8000
echo Keep this window open while you use the app. Close it or press Ctrl+C to stop.
echo.
start "" /min cmd /c "timeout /t 4 /nobreak >nul & start http://localhost:8000"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
echo.
echo The server has stopped.
pause
