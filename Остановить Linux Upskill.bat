@echo off
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0infra\scripts\dev.ps1" halt
echo.
pause
