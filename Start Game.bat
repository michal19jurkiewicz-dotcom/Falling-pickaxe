@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\run.ps1"
if errorlevel 1 (
    echo.
    echo The game exited with an error - see the messages above.
    pause
)
