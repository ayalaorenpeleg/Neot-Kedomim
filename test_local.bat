@echo off
REM Local test for the Neot Kedumim GIS app
cd /d "%~dp0"
start "Neot Kedumim local server" powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0serve.ps1"
timeout /t 3 >nul
start "" "http://localhost:3000/Neot_Kedumim_GIS_Desktop.html"
start "" "http://localhost:3000/Neot_Kedumim_GIS_Mobile.html"
