@echo off
setlocal

title Pocket AI - OpenCode

echo.
echo ==========================================
echo          Pocket AI - OpenCode
echo ==========================================
echo.

REM Find Pocket AI root
set "USB=%~dp0.."

for %%I in ("%USB%") do set "USB=%%~fI"

REM Portable Node + OpenCode
set "NODE_HOME=%USB%\AI\node"
set "OPENCODE_HOME=%USB%\AI\opencode"
set "OPENCODE_CONFIG=%USB%\AI\config\opencode.json"

REM Use portable Node/OpenCode
set "PATH=%NODE_HOME%;%OPENCODE_HOME%;%PATH%"

echo Pocket AI Root:
echo %USB%
echo.

echo Node:
echo %NODE_HOME%
echo.

echo OpenCode:
echo %OPENCODE_HOME%
echo.

echo Config:
echo %OPENCODE_CONFIG%
echo.

REM Check Node
if not exist "%NODE_HOME%\node.exe" (
    echo [ERROR] node.exe not found!
    echo.
    pause
    exit /b 1
)

REM Check OpenCode
if not exist "%OPENCODE_HOME%\opencode.cmd" (
    echo [ERROR] opencode.cmd not found!
    echo.
    pause
    exit /b 1
)

REM Check config
if not exist "%OPENCODE_CONFIG%" (
    echo [WARNING] opencode.json not found!
    echo.
)

echo ==========================================
echo Starting OpenCode...
echo ==========================================
echo.

call "%OPENCODE_HOME%\opencode.cmd"

echo.
echo ==========================================
echo OpenCode exited.
echo Exit code: %ERRORLEVEL%
echo ==========================================
echo.

pause
endlocal
