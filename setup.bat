@echo off
setlocal
title Voxora Voice - Setup
cd /d "%~dp0backend"
echo.
echo ===== Voxora Voice setup =====
echo.
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY goto nopython
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul || goto nopython

if not exist ".venv\Scripts\python.exe" (
  echo Creating a private Python environment...
  %PY% -m venv .venv || goto fail
)
call ".venv\Scripts\activate.bat"
echo Installing the packages. This can take a few minutes...
python -m pip install --upgrade pip >nul 2>nul
pip install -r requirements.txt || goto fail
if not exist ".env" copy ".env.example" ".env" >nul
echo.
echo ===== Setup finished. Now double-click run.bat =====
pause
exit /b 0

:nopython
echo Python 3.10 or newer was not found.
echo Install Python 3.12 from https://www.python.org/downloads/ and tick "Add python.exe to PATH" on the first screen.
echo Then close this window and double-click setup.bat again.
pause
exit /b 1

:fail
echo.
echo Something went wrong. Read the messages above, then see docs\INSTALLATION_AND_RUN_GUIDE.md (Troubleshooting).
pause
exit /b 1
