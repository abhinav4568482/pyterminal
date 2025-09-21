@echo off
REM Launch PyTerminal in a new Command Prompt window
REM This script starts a new window, navigates to the script directory,
REM and runs the Python terminal application

title My Python Terminal
cd /d "%~dp0"
python terminal.py
pause
