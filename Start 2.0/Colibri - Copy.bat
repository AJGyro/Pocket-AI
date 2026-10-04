@echo off
setlocal

title Colibri Launcher

REM Start.bat is inside D:\Start\
REM Go one level up to get D:\
set "USB=%~dp0.."
for %%I in ("%USB%") do set "USB=%%~fI"

set "CLI=%USB%\Colibri\c\coli.cmd"
set "MODEL=%USB%\Colibri\olmoe_merged"

echo ========================================
echo          COLIBRI USB LAUNCHER
echo ========================================
echo.
echo USB ROOT:
echo %USB%
echo.
echo CLI:
echo %CLI%
echo.
echo MODEL:
echo %MODEL%
echo.

REM Check CLI
if not exist "%CLI%" (
    echo ERROR: coli.cmd not found.
    echo Expected:
    echo %CLI%
    echo.
    pause
    exit /b 1
)

echo [OK] coli.cmd found

REM Check model
if not exist "%MODEL%" (
    echo ERROR: olmoe model not found.
    echo Expected:
    echo %MODEL%
    echo.
    pause
    exit /b 1
)

echo [OK] Model found
echo.
echo Starting Colibri...
echo.

call "%CLI%" chat --model "%MODEL%"

echo.
echo Colibri has exited.
pause

endlocal