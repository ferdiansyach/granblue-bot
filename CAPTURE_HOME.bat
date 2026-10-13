@echo off
title Granblue - Capture HOME Button
echo ============================================================
echo   Granblue Automation - Capture HOME Button Tool
echo ============================================================
echo.
echo Pastikan:
echo   * Game Granblue Fantasy terbuka di browser
echo   * Bottom menu (Home/Quest/Menu) terlihat jelas
echo   * Window game di notch ke-2
echo.
echo Script akan berjalan dalam 3 detik...
timeout /t 3 /nobreak > nul
cd /d "%~dp0backend"
python capture_home_button.py
echo.
pause
