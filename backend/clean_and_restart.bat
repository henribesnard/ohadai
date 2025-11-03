@echo off
echo ========================================
echo Nettoyage du cache Python et redemarrage
echo ========================================
echo.

REM Aller dans le repertoire backend
cd /d "%~dp0"

echo [1/5] Arret de tous les processus Python...
FOR /F "tokens=2" %%i IN ('tasklist ^| findstr /I "python.exe"') DO (
    taskkill /F /PID %%i 2>nul
)
FOR /F "tokens=2" %%i IN ('tasklist ^| findstr /I "uvicorn"') DO (
    taskkill /F /PID %%i 2>nul
)
echo OK

echo.
echo [2/5] Nettoyage des fichiers cache __pycache__...
FOR /D /R . %%G IN (__pycache__) DO (
    IF EXIST "%%G" (
        echo Suppression de %%G
        RD /S /Q "%%G" 2>nul
    )
)
echo OK

echo.
echo [3/5] Nettoyage des fichiers .pyc...
FOR /R . %%G IN (*.pyc) DO (
    IF EXIST "%%G" (
        DEL /F /Q "%%G" 2>nul
    )
)
echo OK

echo.
echo [4/5] Attente de 3 secondes...
ping 127.0.0.1 -n 4 > nul
echo OK

echo.
echo [5/5] Demarrage du serveur...
set PYTHONPATH=%CD%
start "OHADA API Server - BGE-M3" cmd /k "python -m uvicorn src.api.ohada_api_server:app --host 0.0.0.0 --port 8000 --reload"

echo.
echo ========================================
echo Serveur lance !
echo ========================================
echo.
echo Attendez 15-20 secondes pour:
echo   - Chargement de BGE-M3 (modele d'embedding)
echo   - Initialisation de ChromaDB
echo   - Chargement des collections (699 documents)
echo.
echo Ensuite, testez avec:
echo   curl -X POST "http://localhost:8000/query" -H "Content-Type: application/json" -d "{\"query\": \"Test\"}"
echo.
echo Verifiez les logs dans: backend\ohada_api_test.log
echo.
pause
