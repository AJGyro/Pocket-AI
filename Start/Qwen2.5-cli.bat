@echo off
setlocal

REM Find USB root
set "USB=%~dp0.."
for %%I in ("%USB%") do set "USB=%%~fI"

REM Paths
set "CLI=%USB%\server\llama-gpu\llama-cli.exe"
set "MODEL=%USB%\Models\qwen2.5-coder-7b-instruct-q4_k_m.gguf"

REM Check CLI
if not exist "%CLI%" (
    echo ERROR: llama-cli.exe not found.
    echo.
    echo Expected:
    echo %CLI%
    pause
    exit /b 1
)

REM Check model
if not exist "%MODEL%" (
    echo ERROR: Qwen2.5 model not found.
    echo.
    echo Expected:
    echo %MODEL%
    pause
    exit /b 1
)

REM Start Qwen2.5 CLI
"%CLI%" ^
    -m "%MODEL%" ^
    -c 16384

endlocal

