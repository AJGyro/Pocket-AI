
@echo off
setlocal EnableDelayedExpansion

title Colibri USB Launcher

:: ============================================================
:: COLIBRI USB LAUNCHER
:: ============================================================

:: Get USB root
set "USB=%~dp0.."
for %%I in ("%USB%") do set "USB=%%~fI"

set "CLI=%USB%\Colibri\c\coli.cmd"
set "MODEL=%USB%\Colibri\olmoe_merged"

:: ============================================================
:: ENABLE ANSI COLORS
:: ============================================================

for /F "delims=" %%A in ('echo prompt $E^| cmd') do set "ESC=%%A"

set "RESET=!ESC![0m"
set "RED=!ESC![91m"
set "GREEN=!ESC![92m"
set "YELLOW=!ESC![93m"
set "BLUE=!ESC![94m"
set "MAGENTA=!ESC![95m"
set "CYAN=!ESC![96m"
set "WHITE=!ESC![97m"
set "BOLD=!ESC![1m"

:: ============================================================
:: CHECK FILES
:: ============================================================

cls

echo.
echo !CYAN!!BOLD!================================================!RESET!
echo !CYAN!!BOLD!              COLIBRI USB AI                 !RESET!
echo !CYAN!!BOLD!================================================!RESET!
echo.
echo !WHITE!USB ROOT : !YELLOW!!USB!!RESET!
echo !WHITE!MODEL    : !YELLOW!!MODEL!!RESET!
echo.

if not exist "!CLI!" (
    echo !RED!!BOLD![ERROR] Colibri CLI not found!RESET!
    echo.
    echo Expected:
    echo !YELLOW!!CLI!!RESET!
    echo.
    pause
    exit /b 1
)

echo !GREEN![OK] Colibri CLI found!RESET!

if not exist "!MODEL!" (
    echo !RED!!BOLD![ERROR] OLMoE model not found!RESET!
    echo.
    echo Expected:
    echo !YELLOW!!MODEL!!RESET!
    echo.
    pause
    exit /b 1
)

echo !GREEN![OK] OLMoE model found!RESET!
echo.

:: ============================================================
:: HARDWARE MENU
:: ============================================================

:hardware

echo !CYAN!!BOLD!------------------------------------------------!RESET!
echo !WHITE!!BOLD!SELECT HARDWARE!RESET!
echo !CYAN!------------------------------------------------!RESET!
echo.
echo   !GREEN![1]!RESET! GPU
echo   !YELLOW![2]!RESET! CPU
echo   !RED![3]!RESET! Exit
echo.

choice /C 123 /N /M "!WHITE!Select option: !RESET!"

if errorlevel 3 goto exit

if errorlevel 2 (
    set "GPU=none"
    set "HARDWARE=CPU"
    goto mode
)

if errorlevel 1 (
    set "GPU=auto"
    set "HARDWARE=GPU"
    goto mode
)

:: ============================================================
:: MODE MENU
:: ============================================================

:mode

cls

echo.
echo !MAGENTA!!BOLD!================================================!RESET!
echo !MAGENTA!!BOLD!              COLIBRI USB AI                 !RESET!
echo !MAGENTA!!BOLD!================================================!RESET!
echo.
echo !WHITE!Hardware selected: !GREEN!!HARDWARE!!RESET!
echo.

echo !CYAN!!BOLD!------------------------------------------------!RESET!
echo !WHITE!!BOLD!SELECT MODE!RESET!
echo !CYAN!------------------------------------------------!RESET!
echo.
echo   !GREEN![1]!RESET! Terminal CLI
echo   !BLUE![2]!RESET! Web Dashboard
echo   !RED![3]!RESET! Back
echo.

choice /C 123 /N /M "!WHITE!Select option: !RESET!"

if errorlevel 3 goto hardware

if errorlevel 2 (
    set "MODE=WEB"
    goto start
)

if errorlevel 1 (
    set "MODE=CLI"
    goto start
)

:: ============================================================
:: START COLIBRI
:: ============================================================

:start

cls

echo.
echo !CYAN!!BOLD!================================================!RESET!
echo !CYAN!!BOLD!             STARTING COLIBRI                 !RESET!
echo !CYAN!!BOLD!================================================!RESET!
echo.
echo !WHITE!Hardware : !GREEN!!HARDWARE!!RESET!
echo !WHITE!Mode     : !GREEN!!MODE!!RESET!
echo !WHITE!Model    : !YELLOW!OLMoE!RESET!
echo.

:: ============================================================
:: OLMoE HARDWARE CHECK
:: ============================================================

if "!HARDWARE!"=="GPU" (
    echo !YELLOW![INFO] GPU selected.!RESET!
    echo !YELLOW![INFO] OLMoE currently supports CPU only.!RESET!
    echo !YELLOW![INFO] Falling back to CPU automatically.!RESET!
    echo.
    set "GPU_ARGS="
) else (
    echo !YELLOW![CPU] CPU execution selected.!RESET!
    echo.
    set "GPU_ARGS="
)

if "!MODE!"=="CLI" goto start_cli
if "!MODE!"=="WEB" goto start_web

goto exit

:: ============================================================
:: TERMINAL CLI
:: ============================================================

:start_cli

echo !GREEN!!BOLD!Starting Colibri Terminal...!RESET!
echo.
echo !CYAN!------------------------------------------------!RESET!
echo.

call "!CLI!" chat --model "!MODEL!"

echo.
echo !CYAN!------------------------------------------------!RESET!
echo !YELLOW!Colibri has exited.!RESET!
echo.

pause
goto exit

:: ============================================================
:: WEB DASHBOARD
:: ============================================================

:start_web

echo !GREEN!!BOLD!Starting Colibri Web Dashboard...!RESET!
echo.
echo !CYAN!The browser dashboard will open automatically.!RESET!
echo.
echo !CYAN!------------------------------------------------!RESET!
echo.

call "!CLI!" web --model "!MODEL!"

echo.
echo !CYAN!------------------------------------------------!RESET!
echo !YELLOW!Colibri Web has exited.!RESET!
echo.

pause
goto exit

:: ============================================================
:: EXIT
:: ============================================================

:exit

echo.
echo !CYAN!Goodbye!RESET!
echo.

endlocal
exit /b 0

