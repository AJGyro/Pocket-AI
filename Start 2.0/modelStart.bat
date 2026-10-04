@echo off
setlocal EnableDelayedExpansion
title Pocket AI Launcher

:: ============================================================
::                     POCKET AI LAUNCHER
:: ============================================================
:: CPU / GPU
:: WEB / CLI
:: Qwen3.5-9B / Qwen2.5-Coder-7B
:: Qwen3.5 Thinking ON / OFF
:: ============================================================


:: ============================================================
:: FIND USB ROOT
:: ============================================================

set "USB=%~dp0.."

for %%I in ("%USB%") do set "USB=%%~fI"


:: ============================================================
:: LLAMA PATHS
:: ============================================================

set "LLAMA_GPU=%USB%\server\llama-gpu"
set "LLAMA_CPU=%USB%\server\llama"

set "GPU_SERVER=%LLAMA_GPU%\llama-server.exe"
set "GPU_CLI=%LLAMA_GPU%\llama-cli.exe"

set "CPU_SERVER=%LLAMA_CPU%\llama-server.exe"
set "CPU_CLI=%LLAMA_CPU%\llama-cli.exe"


:: ============================================================
:: MODEL PATHS
:: ============================================================

set "QWEN35=%USB%\Models\Qwen3.5-9B-The-Defiant-Fable-Uncnr-Heretic-NEO-MAX-Q4_K_M.gguf"

set "QWEN25=%USB%\Models\qwen2.5-coder-7b-instruct-q4_k_m.gguf"


:: ============================================================
:: ANSI COLORS
:: ============================================================

for /F "delims=" %%A in ('echo prompt $E^| cmd') do set "ESC=%%A"

set "RESET=!ESC![0m"
set "BOLD=!ESC![1m"

set "RED=!ESC![91m"
set "GREEN=!ESC![92m"
set "YELLOW=!ESC![93m"
set "BLUE=!ESC![94m"
set "MAGENTA=!ESC![95m"
set "CYAN=!ESC![96m"
set "WHITE=!ESC![97m"


:: ============================================================
:: MAIN MENU
:: ============================================================

:MENU

cls

echo.
echo !CYAN!!BOLD!============================================================!RESET!
echo !CYAN!!BOLD!                    POCKET AI LAUNCHER!RESET!
echo !CYAN!!BOLD!============================================================!RESET!
echo.
echo !WHITE!USB Root : !YELLOW!!USB!!RESET!
echo.
echo !MAGENTA!!BOLD!Select Hardware!RESET!
echo.
echo !GREEN![1]!RESET! GPU
echo !BLUE![2]!RESET! CPU
echo.
echo !RED![3]!RESET! Exit
echo.

choice /C 123 /N /M "Select: "

if errorlevel 3 goto EXIT
if errorlevel 2 (
    set "HARDWARE=CPU"
    goto MODE_MENU
)

if errorlevel 1 (
    set "HARDWARE=GPU"
    goto MODE_MENU
)


:: ============================================================
:: MODE MENU
:: ============================================================

:MODE_MENU

cls

echo.
echo !CYAN!!BOLD!============================================================!RESET!
echo !CYAN!!BOLD!                         POCKET AI!RESET!
echo !CYAN!!BOLD!============================================================!RESET!
echo.
echo Hardware : !YELLOW!!HARDWARE!!RESET!
echo.
echo !MAGENTA!!BOLD!Select Mode!RESET!
echo.
echo !GREEN![1]!RESET! Web Server
echo !BLUE![2]!RESET! CLI / Terminal
echo.
echo !RED![3]!RESET! Back
echo.

choice /C 123 /N /M "Select: "

if errorlevel 3 goto MENU

if errorlevel 2 (
    set "MODE=CLI"
    goto MODEL_MENU
)

if errorlevel 1 (
    set "MODE=WEB"
    goto MODEL_MENU
)


:: ============================================================
:: MODEL MENU
:: ============================================================

:MODEL_MENU

cls

echo.
echo !CYAN!!BOLD!============================================================!RESET!
echo !CYAN!!BOLD!                       SELECT MODEL!RESET!
echo !CYAN!!BOLD!============================================================!RESET!
echo.
echo Hardware : !YELLOW!!HARDWARE!!RESET!
echo Mode     : !YELLOW!!MODE!!RESET!
echo.
echo !MAGENTA!!BOLD!Available Models!RESET!
echo.
echo !GREEN![1]!RESET! Qwen3.5-9B
echo !BLUE![2]!RESET! Qwen2.5-Coder-7B
echo.
echo !RED![3]!RESET! Back
echo.

choice /C 123 /N /M "Select: "

if errorlevel 3 goto MODE_MENU

if errorlevel 2 (
    set "MODEL=%QWEN25%"
    set "MODEL_NAME=Qwen2.5-Coder-7B"
    set "REASONING="
    goto START
)

if errorlevel 1 (
    set "MODEL=%QWEN35%"
    set "MODEL_NAME=Qwen3.5-9B"
    goto REASONING_MENU
)


:: ============================================================
:: QWEN3.5 THINKING MENU
:: ============================================================

:REASONING_MENU

cls

echo.
echo !CYAN!!BOLD!============================================================!RESET!
echo !CYAN!!BOLD!                    QWEN3.5 REASONING!RESET!
echo !CYAN!!BOLD!============================================================!RESET!
echo.
echo Model : !YELLOW!Qwen3.5-9B!RESET!
echo.
echo !MAGENTA!!BOLD!Thinking / Reasoning Mode!RESET!
echo.
echo !GREEN![1]!RESET! Thinking ON
echo !BLUE![2]!RESET! Thinking OFF
echo.
echo !RED![3]!RESET! Back
echo.

choice /C 123 /N /M "Select: "

if errorlevel 3 goto MODEL_MENU

if errorlevel 2 (
    set "REASONING=off"
    goto START
)

if errorlevel 1 (
    set "REASONING=on"
    goto START
)


:: ============================================================
:: START
:: ============================================================

:START

if /I "!MODE!"=="CLI" goto START_CLI

if /I "!MODE!"=="WEB" goto START_WEB

goto MENU


:: ============================================================
:: CLI
:: ============================================================

:START_CLI

cls

echo.
echo !CYAN!!BOLD!============================================================!RESET!
echo !CYAN!!BOLD!                         STARTING CLI!RESET!
echo !CYAN!!BOLD!============================================================!RESET!
echo.
echo Hardware : !YELLOW!!HARDWARE!!RESET!
echo Model    : !YELLOW!!MODEL_NAME!!RESET!

if /I "!MODEL_NAME!"=="Qwen3.5-9B" (
    echo Thinking : !YELLOW!!REASONING!!RESET!
)

echo.
echo Model Path:
echo !WHITE!!MODEL!!RESET!
echo.
echo ------------------------------------------------------------
echo.


:: ============================================================
:: CHECK MODEL
:: ============================================================

if not exist "!MODEL!" (
    echo.
    echo !RED![ERROR] Model file not found.!RESET!
    echo.
    echo Expected:
    echo !MODEL!
    echo.
    pause
    goto MENU
)


:: ============================================================
:: SELECT CPU/GPU
:: ============================================================

if /I "!HARDWARE!"=="GPU" goto GPU_CLI

goto CPU_CLI


:: ============================================================
:: GPU CLI
:: ============================================================

:GPU_CLI

echo !CYAN![GPU] Checking llama-cli...!RESET!
echo.

if not exist "!GPU_CLI!" (
    echo !RED![ERROR] GPU llama-cli.exe not found.!RESET!
    echo.
    echo Expected:
    echo !GPU_CLI!
    echo.
    pause
    goto MENU
)

echo !GREEN![OK] GPU llama-cli found.!RESET!
echo.

echo !GREEN!Starting Qwen CLI...!RESET!
echo.

if /I "!MODEL_NAME!"=="Qwen3.5-9B" (
    echo Reasoning : !YELLOW!!REASONING!!RESET!
)

echo.
echo ------------------------------------------------------------
echo.

cd /d "!LLAMA_GPU!"


:: QWEN3.5
if /I "!MODEL_NAME!"=="Qwen3.5-9B" (
    "!GPU_CLI!" -m "!MODEL!" --jinja --reasoning !REASONING!
    set "EXITCODE=!ERRORLEVEL!"
    goto CLI_FINISHED
)


:: QWEN2.5
"!GPU_CLI!" -m "!MODEL!" --jinja

set "EXITCODE=!ERRORLEVEL!"

goto CLI_FINISHED


:: ============================================================
:: CPU CLI
:: ============================================================

:CPU_CLI

echo !CYAN![CPU] Checking llama-cli...!RESET!
echo.

if not exist "!CPU_CLI!" (
    echo !RED![ERROR] CPU llama-cli.exe not found.!RESET!
    echo.
    echo Expected:
    echo !CPU_CLI!
    echo.
    pause
    goto MENU
)

echo !GREEN![OK] CPU llama-cli found.!RESET!
echo.

echo !GREEN!Starting Qwen CLI...!RESET!
echo.

if /I "!MODEL_NAME!"=="Qwen3.5-9B" (
    echo Reasoning : !YELLOW!!REASONING!!RESET!
)

echo.
echo ------------------------------------------------------------
echo.

cd /d "!LLAMA_CPU!"


:: QWEN3.5
if /I "!MODEL_NAME!"=="Qwen3.5-9B" (
    "!CPU_CLI!" -m "!MODEL!" --jinja --reasoning !REASONING!
    set "EXITCODE=!ERRORLEVEL!"
    goto CLI_FINISHED
)


:: QWEN2.5
"!CPU_CLI!" -m "!MODEL!" --jinja

set "EXITCODE=!ERRORLEVEL!"

goto CLI_FINISHED


:: ============================================================
:: CLI FINISHED
:: ============================================================

:CLI_FINISHED

echo.
echo ------------------------------------------------------------
echo.

if "!EXITCODE!"=="0" (
    echo !GREEN!llama-cli exited normally.!RESET!
) else (
    echo !YELLOW!llama-cli exited with code: !EXITCODE!!RESET!
)

echo.
echo !CYAN!Press any key to return to Pocket AI Launcher.!RESET!
pause >nul

goto MENU


:: ============================================================
:: WEB SERVER
:: ============================================================

:START_WEB

cls

echo.
echo !CYAN!!BOLD!============================================================!RESET!
echo !CYAN!!BOLD!                    STARTING WEB SERVER!RESET!
echo !CYAN!!BOLD!============================================================!RESET!
echo.
echo Hardware : !YELLOW!!HARDWARE!!RESET!
echo Model    : !YELLOW!!MODEL_NAME!!RESET!

if /I "!MODEL_NAME!"=="Qwen3.5-9B" (
    echo Thinking : !YELLOW!!REASONING!!RESET!
)

echo.
echo URL:
echo !GREEN!http://127.0.0.1:8080!RESET!
echo.
echo ------------------------------------------------------------
echo.


:: ============================================================
:: CHECK MODEL
:: ============================================================

if not exist "!MODEL!" (
    echo.
    echo !RED![ERROR] Model file not found.!RESET!
    echo.
    echo Expected:
    echo !MODEL!
    echo.
    pause
    goto MENU
)


:: ============================================================
:: SELECT CPU/GPU
:: ============================================================

if /I "!HARDWARE!"=="GPU" goto GPU_WEB

goto CPU_WEB


:: ============================================================
:: GPU WEB
:: ============================================================

:GPU_WEB

echo !CYAN![GPU] Checking llama-server...!RESET!
echo.

if not exist "!GPU_SERVER!" (
    echo !RED![ERROR] GPU llama-server.exe not found.!RESET!
    echo.
    echo Expected:
    echo !GPU_SERVER!
    echo.
    pause
    goto MENU
)

echo !GREEN![OK] GPU llama-server found.!RESET!
echo.

echo !GREEN!Starting server...!RESET!
echo.

if /I "!MODEL_NAME!"=="Qwen3.5-9B" goto GPU_WEB_QWEN35

:: QWEN2.5 WEB
start "Pocket AI - GPU Server" /D "!LLAMA_GPU!" "!GPU_SERVER!" ^
    -m "!MODEL!" ^
    -c 16384 ^
    --jinja ^
    --alias "!MODEL_NAME!"

goto WEB_STARTED


:: ============================================================
:: GPU QWEN3.5 WEB
:: ============================================================

:GPU_WEB_QWEN35

start "Pocket AI - GPU Server" /D "!LLAMA_GPU!" "!GPU_SERVER!" ^
    -m "!MODEL!" ^
    -c 16384 ^
    --jinja ^
    --reasoning !REASONING! ^
    --alias "!MODEL_NAME!"

goto WEB_STARTED


:: ============================================================
:: CPU WEB
:: ============================================================

:CPU_WEB

echo !CYAN![CPU] Checking llama-server...!RESET!
echo.

if not exist "!CPU_SERVER!" (
    echo !RED![ERROR] CPU llama-server.exe not found.!RESET!
    echo.
    echo Expected:
    echo !CPU_SERVER!
    echo.
    pause
    goto MENU
)

echo !GREEN![OK] CPU llama-server found.!RESET!
echo.

echo !GREEN!Starting server...!RESET!
echo.

if /I "!MODEL_NAME!"=="Qwen3.5-9B" goto CPU_WEB_QWEN35

:: QWEN2.5 WEB
start "Pocket AI - CPU Server" /D "!LLAMA_CPU!" "!CPU_SERVER!" ^
    -m "!MODEL!" ^
    -c 16384 ^
    --jinja ^
    --alias "!MODEL_NAME!"

goto WEB_STARTED


:: ============================================================
:: CPU QWEN3.5 WEB
:: ============================================================

:CPU_WEB_QWEN35

start "Pocket AI - CPU Server" /D "!LLAMA_CPU!" "!CPU_SERVER!" ^
    -m "!MODEL!" ^
    -c 16384 ^
    --jinja ^
    --reasoning !REASONING! ^
    --alias "!MODEL_NAME!"

goto WEB_STARTED


:: ============================================================
:: WEB STARTED
:: ============================================================

:WEB_STARTED

timeout /t 3 /nobreak >nul

cls

echo.
echo !CYAN!!BOLD!============================================================!RESET!
echo !CYAN!!BOLD!                     SERVER STARTED!RESET!
echo !CYAN!!BOLD!============================================================!RESET!
echo.
echo Hardware : !GREEN!!HARDWARE!!RESET!
echo Model    : !YELLOW!!MODEL_NAME!!RESET!

if /I "!MODEL_NAME!"=="Qwen3.5-9B" (
    echo Thinking : !YELLOW!!REASONING!!RESET!
)

echo.
echo URL:
echo !GREEN!!BOLD!http://127.0.0.1:8080!RESET!
echo.
echo ------------------------------------------------------------
echo.
echo !GREEN![OK] llama-server process started.!RESET!
echo.
echo !WHITE!The llama-server is running in a separate terminal.!RESET!
echo !WHITE!Keep that terminal open while using the Web UI.!RESET!
echo.
echo !YELLOW!Open in browser:!RESET!
echo !GREEN!http://127.0.0.1:8080!RESET!
echo.
echo ------------------------------------------------------------
echo.
echo !CYAN!Press any key to return to the launcher.!RESET!

pause >nul

goto MENU


:: ============================================================
:: EXIT
:: ============================================================

:EXIT

cls

echo.
echo !CYAN!!BOLD!============================================================!RESET!
echo !CYAN!!BOLD!                       POCKET AI!RESET!
echo !CYAN!!BOLD!============================================================!RESET!
echo.
echo !GREEN!Thank you for using Pocket AI.!RESET!
echo.

timeout /t 2 /nobreak >nul

endlocal
exit /b