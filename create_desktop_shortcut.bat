@echo off
:: ===================================================
::   Create Desktop Shortcut for NRIS
::   Run this once to create a shortcut on your desktop
:: ===================================================

setlocal EnableDelayedExpansion

echo ===================================================
echo   NRIS Desktop Shortcut Creator
echo ===================================================
echo.
echo Choose shortcut type:
echo   1. Normal - Shows console window while running
echo   2. Silent - Minimizes console window (cleaner desktop)
echo.
set /p CHOICE="Enter choice (1 or 2, default=2): "
if "%CHOICE%"=="" set CHOICE=2
echo.

:: Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

:: Get desktop path
set "DESKTOP=%USERPROFILE%\Desktop"

:: Shortcut name
set "SHORTCUT_NAME=NRIS - Patient Registry"

:: Determine target based on choice
if "%CHOICE%"=="1" (
    set "TARGET_FILE=start_NRIS_v2.bat"
    set "WINDOW_STYLE=1"
) else (
    set "TARGET_FILE=start_NRIS_silent.vbs"
    set "WINDOW_STYLE=1"
)

echo Creating desktop shortcut...
echo Source: %SCRIPT_DIR%\%TARGET_FILE%
echo Destination: %DESKTOP%\%SHORTCUT_NAME%.lnk
echo.

:: Create VBS script to make shortcut (Windows doesn't have native shortcut creation)
set "VBS_FILE=%TEMP%\create_shortcut.vbs"

(
echo Set oWS = WScript.CreateObject^("WScript.Shell"^)
echo sLinkFile = "%DESKTOP%\%SHORTCUT_NAME%.lnk"
echo Set oLink = oWS.CreateShortcut^(sLinkFile^)
echo oLink.TargetPath = "%SCRIPT_DIR%\%TARGET_FILE%"
echo oLink.WorkingDirectory = "%SCRIPT_DIR%"
echo oLink.Description = "NIPT Result Interpretation System - Patient Registry"
echo oLink.IconLocation = "shell32.dll,21"
echo oLink.Save
) > "%VBS_FILE%"

:: Run the VBS script to create shortcut
cscript //nologo "%VBS_FILE%"

:: Clean up
del "%VBS_FILE%" >nul 2>&1

:: Check if shortcut was created
if exist "%DESKTOP%\%SHORTCUT_NAME%.lnk" (
    echo.
    echo ===================================================
    echo   SUCCESS! Desktop shortcut created!
    echo ===================================================
    echo.
    echo You can now launch NRIS directly from your desktop.
    echo Look for: "%SHORTCUT_NAME%"
    echo.
    echo The shortcut will:
    echo   - Start the NRIS application
    echo   - Automatically open your browser
    echo   - No need to navigate to folders anymore!
    echo.
) else (
    echo.
    echo [ERROR] Failed to create shortcut
    echo You may need to run this as administrator
    echo.
)

echo Press any key to close...
pause >nul
