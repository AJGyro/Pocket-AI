@echo off

setlocal

title Meta Llama 3.1 8B - Pocket AI Server

echo.

echo ==========================================

echo       Meta Llama 3.1 8B - SERVER

echo ==========================================

echo.

REM Find USB root
set "USB=%~dp0.."

for %%I in ("%USB%") do set "USB=%%~fI"

REM Paths
set "SERVER=%USB%\server\llama-gpu\llama-server.exe"
set "MODEL=%USB%\Models\Meta-Llama-3.1-8B-Instruct-Q5_K_M.gguf"

echo USB:
echo %USB%

echo.

echo SERVER:
echo %SERVER%

echo.

echo MODEL:
echo %MODEL%

echo.

REM Check server
if not exist "%SERVER%" (
    echo ERROR: llama-server.exe not found!
    echo.
    pause
    exit /b 1
)

REM Check model
if not exist "%MODEL%" (
    echo ERROR: Meta Llama 3.1 model not found!
    echo.
    pause
    exit /b 1
)

echo ==========================================
echo Starting llama-server...
echo ==========================================
echo.

"%SERVER%" ^
    -m "%MODEL%" ^
    -ngl 99 ^
    -c 8192 ^
    --jinja ^
    --alias "llama-3.1-8b" ^
    --host 127.0.0.1 ^
    --port 8080

echo.

echo ==========================================
echo llama-server exited.
echo Exit code: %ERRORLEVEL%
echo ==========================================

echo.

pause

endlocal
