@echo off

setlocal

REM Find USB root
set "USB=%~dp0.."

for %%I in ("%USB%") do set "USB=%%~fI"

REM Paths
set "SERVER=%USB%\server\llama\llama-server.exe"
set "MODEL=%USB%\Models\UI-TARS-2B-SFT-Q6_K.gguf"
set "MMPROJ=%USB%\Models\mmproj-model-f16.gguf"

REM Check server
if not exist "%SERVER%" (
    echo ERROR: llama-server.exe not found.
    echo.
    echo Expected:
    echo %SERVER%
    pause
    exit /b 1
)

REM Check UI-TARS model
if not exist "%MODEL%" (
    echo ERROR: UI-TARS model not found.
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
echo Starting UI-TARS...
echo Model:
echo %MODEL%
echo.
echo Projector:
echo %MMPROJ%
echo.

"%SERVER%" ^
    -m "%MODEL%" ^
    --mmproj "%MMPROJ%" ^
    -c 16384 ^
    --jinja ^
    --alias "ui-tars-2b"

endlocal