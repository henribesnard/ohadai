@echo off
echo Killing all Python processes...
taskkill /F /IM python.exe 2>nul
timeout /t 3 /nobreak >nul

echo Cleaning Python cache...
cd backend
del /S /Q *.pyc 2>nul
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul

echo Starting server...
set PYTHONPATH=%CD%
start "OHADA Server" cmd /k "python -m uvicorn src.api.ohada_api_server:app --host 0.0.0.0 --port 8000 --reload"

echo Done! Wait 20 seconds for BGE-M3 to load.
