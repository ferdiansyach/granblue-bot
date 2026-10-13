@echo off
title Granblue Automation - ROTB Lvl 100 Shenxian Launcher
echo.
echo ================================================
echo  ROTB Shenxian Lvl 100 - Launcher Script
echo ================================================
echo.

cd /d "%~dp0"

:: Patch settings.json to Lvl 100 Shenxian
python -c "import json; f=open(\"backend/settings.json\",\"r\"); d=json.load(f); f.close(); d[\"game\"][\"mission\"]=\"Lvl 100 Shenxian\"; d[\"game\"][\"farmingMode\"]=\"Rise of the Beasts\"; f=open(\"backend/settings.json\",\"w\"); json.dump(d,f,indent=4); f.close(); print(\"[OK] Mission set to: Lvl 100 Shenxian\")"

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Gagal update settings.json
    pause
    exit /b 1
)

echo.
echo [INFO] settings.json berhasil diupdate ke Lvl 100 Shenxian
echo [INFO] Sekarang jalankan Granblue Automation.exe
echo.
pause
