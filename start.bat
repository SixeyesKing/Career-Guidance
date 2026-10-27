@echo off
setlocal

rem Always run from the folder containing this batch file.
cd /d "%~dp0"
set "PYTHON=%~dp0.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo [ERROR] Project virtual environment was not found:
    echo         "%PYTHON%"
    echo Create it from this folder with: python -m venv .venv
    pause
    exit /b 1
)

start "Career Guidance API" cmd /k ""%PYTHON%" -m uvicorn app.api:app --host 127.0.0.1 --port 8002"
start "Career Guidance UI" cmd /k ""%PYTHON%" -m streamlit run app/ui.py --server.address 127.0.0.1 --server.port 8501 --server.headless true"

timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8501"

endlocal
