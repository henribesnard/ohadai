@echo off
echo Killing all processes on port 8000...
FOR /F "tokens=5" %%P IN ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') DO (
    echo Killing PID %%P
    taskkill /F /PID %%P 2>nul
)
echo.
echo Waiting 3 seconds...
ping 127.0.0.1 -n 4 > nul
echo.
echo Starting server from backend directory...
cd /d "%~dp0"
start "OHADA API Server" cmd /k "uvicorn src.api.ohada_api_server:app --host 0.0.0.0 --port 8000 --reload"
echo.
echo Server should be starting... Wait 10 seconds before testing.
