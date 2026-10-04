@echo off
setlocal

REM Find USB root
set "USB=%~dp0.."
for %%I in ("%USB%") do set "USB=%%~fI"

REM Paths
set "SERVER=%USB%\server\llama-gpu\llama-server.exe"
set "MODEL=%USB%\Models\qwen2.5-coder-7b-instruct-q4_k_m.gguf"

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
    echo ERROR: Qwen2.5 model not found.
    echo.
    echo Expected:
    echo %MODEL%
    pause
    exit /b 1
)

REM Start Qwen2.5 GPU server
"%SERVER%" ^
    -m "%MODEL%" ^
    -c 16384 ^
    --jinja ^
    --alias "qwen2.5-coder-7b"

endlocal

