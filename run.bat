@echo off
TITLE Mastering App - HYPER DEBUG
SETLOCAL EnableDelayedExpansion

:: 1. TRY TO FIND PROJECT FOLDER
SET "PROJECT_DIR=D:\MasteringApp"

echo ========================================
echo        DIAGNOSTIC BOOT SEQUENCE
echo ========================================
echo TIME: %TIME%
echo RUNNING FROM: %~dp0
echo TARGET PATH: %PROJECT_DIR%
echo.

:: 2. JUMP TO DRIVE
D:
if %ERRORLEVEL% neq 0 (
    echo [CRITICAL ERROR] COULD NOT ACCESS D: DRIVE
    pause
    exit /b
)

:: 3. JUMP TO FOLDER
cd /d "%PROJECT_DIR%"
if %ERRORLEVEL% neq 0 (
    echo [CRITICAL ERROR] COULD NOT ACCESS FOLDER: %PROJECT_DIR%
    pause
    exit /b
)
echo [STATUS] CD SUCCESSFUL. CURRENT DIR: %CD%

:: 4. CHECK PYTHON
if not exist "venv\Scripts\python.exe" (
    echo [CRITICAL ERROR] PYTHON NOT FOUND AT: %CD%\venv\Scripts\python.exe
    dir /s venv
    pause
    exit /b
)
echo [STATUS] PYTHON BINARY VERIFIED.

:: 5. LAUNCH WITH LOGGING
echo.
echo [STATUS] EXECUTING MAIN.PY...
echo ----------------------------------------
"venv\Scripts\python.exe" main.py
echo ----------------------------------------
echo [STATUS] CODE EXITED WITH: %ERRORLEVEL%

echo.
echo THE WINDOW WILL NOT CLOSE UNTIL YOU PRESS A KEY.
pause
