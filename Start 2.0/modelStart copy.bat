@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ============================================================
REM                    PORTABLE AI
REM ============================================================

REM ============================================================
REM FIND USB ROOT
REM ModelStart.bat is inside:
REM USB:\START\ModelStart.bat
REM ============================================================

set "USB=%~dp0.."
for %%I in ("%USB%") do set "USB=%%~fI"

REM ============================================================
REM PATHS
REM ============================================================

REM GPU llama.cpp
set "LLAMA_GPU=%USB%\server\llama-gpu"

REM CPU llama.cpp
set "LLAMA_CPU=%USB%\server\llama"

REM Models
set "MODEL_HOME=%USB%\Models"

REM ============================================================
REM EXECUTABLES
REM ============================================================

set "GPU_SERVER=%LLAMA_GPU%\llama-server.exe"
set "GPU_CLI=%LLAMA_GPU%\llama-cli.exe"

set "CPU_SERVER=%LLAMA_CPU%\llama-server.exe"
set "CPU_CLI=%LLAMA_CPU%\llama-cli.exe"

REM ============================================================
REM MODELS
REM ============================================================

set "QWEN35=%MODEL_HOME%\Qwen3.5-9B-The-Defiant-Fable-Uncnr-Heretic-NEO-MAX-Q4_K_M.gguf"

set "QWEN25=%MODEL_HOME%\qwen2.5-coder-7b-instruct-q4_k_m.gguf"


REM ============================================================
REM MENU
REM ============================================================

:MENU

cls


echo.
echo ========================================
echo              PORTABLE AI
echo ========================================
echo.
echo USB ROOT:
echo %USB%
echo.
echo ----------------------------------------
echo.
echo [1] Qwen3.5-9B        [GPU Server]
echo [2] Qwen2.5-Coder-7B  [GPU Server]
echo.
echo [3] Qwen3.5 CLI       [GPU]
echo [4] Qwen2.5 CLI       [GPU]
echo.
echo [5] Qwen3.5 CLI       [CPU]
echo [6] Qwen2.5 CLI       [CPU]
echo.
echo [7] Exit
echo.
echo ----------------------------------------
echo.

set /p "CHOICE=Select: "

if "%CHOICE%"=="1" goto QWEN35_GPU_SERVER
if "%CHOICE%"=="2" goto QWEN25_GPU_SERVER
if "%CHOICE%"=="3" goto QWEN35_GPU_CLI
if "%CHOICE%"=="4" goto QWEN25_GPU_CLI
if "%CHOICE%"=="5" goto QWEN35_CPU_CLI
if "%CHOICE%"=="6" goto QWEN25_CPU_CLI
if "%CHOICE%"=="7" goto EXIT

echo.
echo Invalid choice.
timeout /t 2 >nul
goto MENU


REM ============================================================
REM QWEN3.5 GPU SERVER
REM ============================================================

:QWEN35_GPU_SERVER

cls

echo.
echo ========================================
echo        Qwen3.5-9B GPU SERVER
echo ========================================
echo.

if not exist "%GPU_SERVER%" (
    echo ERROR:
    echo GPU llama-server.exe not found.
    echo.
    echo Expected:
    echo %GPU_SERVER%
    echo.
    pause
    goto MENU
)

if not exist "%QWEN35%" (
    echo ERROR:
    echo Qwen3.5 model not found.
    echo.
    echo Expected:
    echo %QWEN35%
    echo.
    pause
    goto MENU
)

echo GPU Engine:
echo %GPU_SERVER%
echo.
echo Model:
echo %QWEN35%
echo.
echo Server:
echo http://127.0.0.1:8080
echo.
echo Starting Qwen3.5 GPU server...
echo.

REM Start server in a NEW console window.
REM The main menu will remain open.

start "Qwen3.5-9B GPU Server" /D "%LLAMA_GPU%" "%GPU_SERVER%" ^
  -m "%QWEN35%" ^
  -c 16384 ^
  --jinja ^
  --alias "qwen3.5-9b"

echo.
echo ========================================
echo Qwen3.5 GPU server started.
echo ========================================
echo.
echo Server window opened separately.
echo.
echo Returning to menu...
timeout /t 2 >nul

goto MENU


REM ============================================================
REM QWEN2.5 GPU SERVER
REM ============================================================

:QWEN25_GPU_SERVER

cls

echo.
echo ========================================
echo       Qwen2.5-Coder-7B GPU SERVER
echo ========================================
echo.

if not exist "%GPU_SERVER%" (
    echo ERROR:
    echo GPU llama-server.exe not found.
    echo.
    echo Expected:
    echo %GPU_SERVER%
    echo.
    pause
    goto MENU
)

if not exist "%QWEN25%" (
    echo ERROR:
    echo Qwen2.5 model not found.
    echo.
    echo Expected:
    echo %QWEN25%
    echo.
    pause
    goto MENU
)

echo GPU Engine:
echo %GPU_SERVER%
echo.
echo Model:
echo %QWEN25%
echo.
echo Server:
echo http://127.0.0.1:8080
echo.
echo Starting Qwen2.5 GPU server...
echo.

REM Start server in a NEW console window.

start "Qwen2.5-Coder-7B GPU Server" /D "%LLAMA_GPU%" "%GPU_SERVER%" ^
  -m "%QWEN25%" ^
  -c 16384 ^
  --jinja ^
  --alias "qwen2.5-coder-7b"

echo.
echo ========================================
echo Qwen2.5 GPU server started.
echo ========================================
echo.
echo Server window opened separately.
echo.
echo Returning to menu...
timeout /t 2 >nul

goto MENU


REM ============================================================
REM QWEN3.5 GPU CLI
REM ============================================================

:QWEN35_GPU_CLI

cls

echo.
echo ========================================
echo          Qwen3.5-9B GPU CLI
echo ========================================
echo.

if not exist "%GPU_CLI%" (
    echo ERROR:
    echo GPU llama-cli.exe not found.
    echo.
    echo Expected:
    echo %GPU_CLI%
    echo.
    pause
    goto MENU
)

if not exist "%QWEN35%" (
    echo ERROR:
    echo Qwen3.5 model not found.
    echo.
    echo Expected:
    echo %QWEN35%
    echo.
    pause
    goto MENU
)

echo GPU Engine:
echo %GPU_CLI%
echo.
echo Model:
echo %QWEN35%
echo.
echo Starting Qwen3.5 GPU CLI...
echo.

cd /d "%LLAMA_GPU%"

"%GPU_CLI%" ^
  -m "%QWEN35%"

echo.
echo ========================================
echo Qwen3.5 GPU CLI closed.
echo ========================================
echo.
pause

goto MENU


REM ============================================================
REM QWEN2.5 GPU CLI
REM ============================================================

:QWEN25_GPU_CLI

cls

echo.
echo ========================================
echo        Qwen2.5-Coder-7B GPU CLI
echo ========================================
echo.

if not exist "%GPU_CLI%" (
    echo ERROR:
    echo GPU llama-cli.exe not found.
    echo.
    echo Expected:
    echo %GPU_CLI%
    echo.
    pause
    goto MENU
)

if not exist "%QWEN25%" (
    echo ERROR:
    echo Qwen2.5 model not found.
    echo.
    echo Expected:
    echo %QWEN25%
    echo.
    pause
    goto MENU
)

echo GPU Engine:
echo %GPU_CLI%
echo.
echo Model:
echo %QWEN25%
echo.
echo Starting Qwen2.5 GPU CLI...
echo.

cd /d "%LLAMA_GPU%"

"%GPU_CLI%" ^
  -m "%QWEN25%"

echo.
echo ========================================
echo Qwen2.5 GPU CLI closed.
echo ========================================
echo.
pause

goto MENU


REM ============================================================
REM QWEN3.5 CPU CLI
REM ============================================================

:QWEN35_CPU_CLI

cls

echo.
echo ========================================
echo          Qwen3.5-9B CPU CLI
echo ========================================
echo.

if not exist "%CPU_CLI%" (
    echo ERROR:
    echo CPU llama-cli.exe not found.
    echo.
    echo Expected:
    echo %CPU_CLI%
    echo.
    pause
    goto MENU
)

if not exist "%QWEN35%" (
    echo ERROR:
    echo Qwen3.5 model not found.
    echo.
    echo Expected:
    echo %QWEN35%
    echo.
    pause
    goto MENU
)

echo CPU Engine:
echo %CPU_CLI%
echo.
echo Model:
echo %QWEN35%
echo.
echo Starting Qwen3.5 CPU CLI...
echo.

cd /d "%LLAMA_CPU%"

"%CPU_CLI%" ^
  -m "%QWEN35%"

echo.
echo ========================================
echo Qwen3.5 CPU CLI closed.
echo ========================================
echo.
pause

goto MENU


REM ============================================================
REM QWEN2.5 CPU CLI
REM ============================================================

:QWEN25_CPU_CLI

cls

echo.
echo ========================================
echo        Qwen2.5-Coder-7B CPU CLI
echo ========================================
echo.

if not exist "%CPU_CLI%" (
    echo ERROR:
    echo CPU llama-cli.exe not found.
    echo.
    echo Expected:
    echo %CPU_CLI%
    echo.
    pause
    goto MENU
)

if not exist "%QWEN25%" (
    echo ERROR:
    echo Qwen2.5 model not found.
    echo.
    echo Expected:
    echo %QWEN25%
    echo.
    pause
    goto MENU
)

echo CPU Engine:
echo %CPU_CLI%
echo.
echo Model:
echo %QWEN25%
echo.
echo Starting Qwen2.5 CPU CLI...
echo.

cd /d "%LLAMA_CPU%"

"%CPU_CLI%" ^
  -m "%QWEN25%"

echo.
echo ========================================
echo Qwen2.5 CPU CLI closed.
echo ========================================
echo.
pause

goto MENU


REM ============================================================
REM EXIT
REM ============================================================

:EXIT

cls

echo.
echo ========================================
echo        Exiting Portable AI
echo ========================================
echo.

endlocal
exit /b
