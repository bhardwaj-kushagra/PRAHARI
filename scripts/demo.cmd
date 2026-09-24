@echo off
rem PRAHARI-SIM demo launcher for Windows: double-click to serve the dashboard and open it in presenter mode.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0demo.ps1" %*
