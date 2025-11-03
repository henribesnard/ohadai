@echo off
echo ====================================
echo Arret force de tous les serveurs...
echo ====================================

REM Tuer tous les processus Python et Uvicorn
FOR /F "tokens=2" %%i IN ('tasklist ^| findstr /I "python.exe"') DO (
    echo Arret du processus Python %%i
    taskkill /F /PID %%i 2>nul
)

FOR /F "tokens=2" %%i IN ('tasklist ^| findstr /I "uvicorn"') DO (
    echo Arret du processus Uvicorn %%i
    taskkill /F /PID %%i 2>nul
)

echo.
echo Attente de 3 secondes...
ping 127.0.0.1 -n 4 > nul

echo.
echo ====================================
echo Demarrage du nouveau serveur...
echo ====================================
cd /d "%~dp0"
set PYTHONPATH=%CD%
start "OHADA API Server" uvicorn src.api.ohada_api_server:app --host 0.0.0.0 --port 8000 --reload

echo.
echo Serveur demarre ! Attendez 10-15 secondes pour le chargement de BGE-M3
echo.
pause
