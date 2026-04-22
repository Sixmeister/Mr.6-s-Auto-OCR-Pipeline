@echo off
setlocal
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File ".\start_release_v1_0_debug.ps1"
endlocal
