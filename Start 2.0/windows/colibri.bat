@echo off
setlocal EnableExtensions
title Pocket AI - Colibri (Windows)

set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"

set "CLI=%ROOT%\Colibri\c\coli.cmd"
set "MODEL=%ROOT%\Colibri\olmoe_merged"

echo ==========================================
echo        POCKET AI - COLIBRI
echo ==========================================
echo Root: %ROOT%
echo.

if not exist "%CLI%" (
  echo [ERROR] Colibri CLI not found:
  echo %CLI%
  pause
  exit /b 1
)

if not exist "%MODEL%" (
  echo [ERROR] Colibri model not found:
  echo %MODEL%
  pause
  exit /b 1
)

echo [1] Terminal CLI
echo [2] Web Dashboard
echo [3] Exit
echo.
choice /C 123 /N /M "Select: "

if errorlevel 3 exit /b 0
if errorlevel 2 goto WEB
goto CLI

:CLI
call "%CLI%" chat --model "%MODEL%"
goto END

:WEB
call "%CLI%" web --model "%MODEL%"

:END
echo.
echo Colibri exited.
pause
endlocal
