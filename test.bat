@echo off
title Voxora Voice - Tests
cd /d "%~dp0backend"
call ".venv\Scripts\activate.bat"
python -m unittest discover -s tests -v
echo.
pause
