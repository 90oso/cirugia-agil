@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Ejecuta primero INSTALAR.bat.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" run.py
if errorlevel 1 pause
