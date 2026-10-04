@echo off
setlocal

title Meta Llama 3.1 8B - Pocket AI

echo.
echo ==========================================
echo       Meta Llama 3.1 8B - CLI
echo ==========================================
echo.

REM Find USB root
set "USB=%~dp0.."

for %%I in ("%USB%") do set "USB=%%~fI"

REM Paths
set "CLI=%USB%\server\llama-gpu\llama-cli.exe"
set "MODEL=%USB%\Models\Meta-Llama-3.1-8B-Instruct-Q5_K_M.gguf"

echo USB:
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
    echo ERROR: llama-cli.exe not found!
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
echo Starting llama-cli...
echo ==========================================
echo.

"%CLI%" ^
    -m "%MODEL%" ^
    -ngl 99 ^
    -c 8192 ^
    --jinja

echo.
echo ==========================================
echo llama-cli exited.
echo Exit code: %ERRORLEVEL%
echo ==========================================
echo.

pause
endlocal

