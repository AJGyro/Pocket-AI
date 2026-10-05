@echo off
setlocal

REM Find USB root
set "USB=%~dp0.."
for %%I in ("%USB%") do set "USB=%%~fI"

REM Paths
set "SERVER=%USB%\server\llama-gpu\llama-server.exe"

set "MODEL=%USB%\Models\Qwen3.5-9B-The-Defiant-Fable-Uncnr-Heretic-NEO-MAX-Q4_K_M.gguf"

set "MMPROJ=%USB%\Models\mmproj-F32.gguf"

REM Check server
if not exist "%SERVER%" (
    echo ERROR: llama-server.exe not found.
    echo.
    echo Expected:
    echo %SERVER%
    pause
    exit /b 1
)

REM Check Qwen3.5 model
if not exist "%MODEL%" (
    echo ERROR: Qwen3.5 model not found.
    echo.
    echo Expected:
    echo %MODEL%
    pause
    exit /b 1
)

REM Check projector
if not exist "%MMPROJ%" (
    echo ERROR: mmproj model not found.
    echo.
    echo Expected:
    echo %MMPROJ%
    pause
    exit /b 1
)

echo.
echo ========================================
echo        Pocket AI - Qwen3.5 Vision
echo ========================================
echo.
echo Model:
echo %MODEL%
echo.
echo Projector:
echo %MMPROJ%
echo.
echo Starting llama-server...
echo.

"%SERVER%" ^
    -m "%MODEL%" ^
    --mmproj "%MMPROJ%" ^
    -c 16384 ^
    --jinja --reasoning off ^
    --alias "qwen3.5-9b"

endlocal