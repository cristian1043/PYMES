@echo off
chcp 65001 >nul
echo ========================================================
echo   REINICIANDO SERVIDORES PYMES_BE (5000) Y PYMES_FE (5001)
echo ========================================================

echo [1/3] Deteniendo procesos Python anteriores en puertos 5000 y 5001...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5000 " ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5001 " ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1

echo [2/3] Iniciando Backend PYMES_BE en puerto 5000...
start "PYMES_BE (Puerto 5000)" cmd /k "cd /d %~dp0PYMES_BE && python src/app.py"

timeout /t 2 /nobreak >nul

echo [3/3] Iniciando Frontend Web PYMES_FE en puerto 5001...
start "PYMES_FE (Puerto 5001)" cmd /k "cd /d %~dp0PYMES_FE && python src/app.py"

echo.
echo Listo! Ya puedes recargar tu navegador en http://127.0.0.1:5001
pause
