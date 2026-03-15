@echo off
TITLE Mastering Console - SPECTRAL PROFILE LAB (feature branch)
SETLOCAL EnableDelayedExpansion

:: 1. PROJECT FOLDER
SET "PROJECT_DIR=D:\MasteringApp"
SET "BRANCH=feature/spectral-profile-library"

echo ========================================
echo    Mastering Console - SPECTRAL LAB
echo    Branch: %BRANCH%
echo    ** EXPERIMENTAL - Development Build **
echo ========================================
echo TIME: %TIME%
echo RUNNING FROM: %~dp0
echo.

:: 2. JUMP TO DRIVE AND FOLDER
D:
cd /d "%PROJECT_DIR%"
if %ERRORLEVEL% neq 0 (
    echo [CRITICAL ERROR] COULD NOT ACCESS FOLDER: %PROJECT_DIR%
    pause
    exit /b
)
echo [STATUS] CD SUCCESSFUL. CURRENT DIR: %CD%

:: 3. SWITCH TO FEATURE BRANCH
echo [STATUS] Switching to %BRANCH%...
git checkout %BRANCH% >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Could not switch to %BRANCH%. Continuing anyway.
) else (
    echo [STATUS] Branch: %BRANCH% (SPECTRAL PROFILE LAB)
)

:: 4. CHECK PYTHON
if not exist "venv\Scripts\python.exe" (
    echo [CRITICAL ERROR] PYTHON NOT FOUND AT: %CD%\venv\Scripts\python.exe
    pause
    exit /b
)
echo [STATUS] PYTHON BINARY VERIFIED.

:: 5. LAUNCH
echo.
echo [STATUS] EXECUTING MAIN.PY (Spectral Lab build)...
echo ----------------------------------------
"venv\Scripts\python.exe" main.py
echo ----------------------------------------
echo [STATUS] CODE EXITED WITH: %ERRORLEVEL%

echo.
echo THE WINDOW WILL NOT CLOSE UNTIL YOU PRESS A KEY.
pause
