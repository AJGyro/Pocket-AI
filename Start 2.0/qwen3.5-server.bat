@echo off
setlocal

REM Find USB root
set "USB=%~dp0.."
for %%I in ("%USB%") do set "USB=%%~fI"

REM Paths
set "SERVER=%USB%\server\llama-gpu\llama-server.exe"
set "MODEL=%USB%\Models\Qwen3.5-9B-The-Defiant-Fable-Uncnr-Heretic-NEO-MAX-Q4_K_M.gguf"

REM Check server
if not exist "%SERVER%" (
    echo ERROR: llama-server.exe not found.
    echo.
    echo Expected:
    echo %SERVER%
    pause
    exit /b 1
)

REM Check model
if not exist "%MODEL%" (
    echo ERROR: Qwen3.5 model not found.
    echo.
    echo Expected:
    echo %MODEL%
    pause
    exit /b 1
)

REM Start server in this terminal
"%SERVER%" ^
    -m "%MODEL%" ^
    -c 16384 ^
    --jinja ^
    --alias "qwen3.5-9b"

endlocal
