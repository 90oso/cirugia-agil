@echo off
setlocal
cd /d "%~dp0"
echo Preparando Cirugia Agil...
where py >nul 2>nul
if %errorlevel% equ 0 (
  py -3 -m venv .venv
) else (
  python -m venv .venv
)
if errorlevel 1 goto error
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto error
if not exist .env copy .env.example .env >nul
echo.
echo Instalacion lista. Abre Ollama y ejecuta INICIAR.bat.
echo Si no tienes modelo, ejecuta: ollama pull qwen3:4b
pause
exit /b 0
:error
echo.
echo No se pudo instalar. Revisa el mensaje anterior y que Python 3.11 o superior este instalado.
pause
exit /b 1
