@echo off
title Granblue Automation - ROTB Lvl 150 Shenxian Launcher
echo.
echo ================================================
echo  ROTB Shenxian Lvl 150 - Launcher Script
echo ================================================
echo.

cd /d "%~dp0"

:: Patch settings.json to Lvl 150 Shenxian
python -c "import json; f=open(\"backend/settings.json\",\"r\"); d=json.load(f); f.close(); d[\"game\"][\"mission\"]=\"Lvl 150 Shenxian\"; d[\"game\"][\"farmingMode\"]=\"Rise of the Beasts\"; f=open(\"backend/settings.json\",\"w\"); json.dump(d,f,indent=4); f.close(); print(\"[OK] Mission set to: Lvl 150 Shenxian\")"

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Gagal update settings.json
    pause
    exit /b 1
)

echo.
echo [INFO] settings.json berhasil diupdate ke Lvl 150 Shenxian
echo [INFO] Sekarang jalankan Granblue Automation.exe
echo.
echo [PENTING] Setelah membuka GUI:
echo   - Jangan ganti Mission di dropdown (akan reset ke Lvl 100)
echo   - Jika sudah terganti, tutup GUI dan jalankan script ini lagi
echo.
pause
