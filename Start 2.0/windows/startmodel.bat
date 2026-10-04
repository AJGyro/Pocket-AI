@echo off
setlocal EnableExtensions
title Pocket AI - Model Launcher (Windows)

set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"

set "GPU=%ROOT%\server\llama-gpu"
set "CPU=%ROOT%\server\llama"
set "GPU_SERVER=%GPU%\llama-server.exe"
set "GPU_CLI=%GPU%\llama-cli.exe"
set "CPU_SERVER=%CPU%\llama-server.exe"
set "CPU_CLI=%CPU%\llama-cli.exe"

set "Q35=%ROOT%\Models\Qwen3.5-9B-The-Defiant-Fable-Uncnr-Heretic-NEO-MAX-Q4_K_M.gguf"
set "Q25=%ROOT%\Models\qwen2.5-coder-7b-instruct-q4_k_m.gguf"

:MENU
cls
echo ==========================================
echo          POCKET AI MODEL START
echo ==========================================
echo [1] Qwen3.5-9B
echo [2] Qwen2.5-Coder-7B
echo [3] Exit
choice /C 123 /N /M "Model: "

if errorlevel 3 exit /b 0
if errorlevel 2 (
  set "MODEL=%Q25%"
  set "NAME=Qwen2.5-Coder-7B"
  goto TYPE
)
set "MODEL=%Q35%"
set "NAME=Qwen3.5-9B"

:TYPE
cls
echo Model: %NAME%
echo [1] GPU Server
echo [2] CPU Server
echo [3] GPU CLI
echo [4] CPU CLI
echo [5] Back
choice /C 12345 /N /M "Mode: "

if errorlevel 5 goto MENU
if errorlevel 4 goto CPUCLI
if errorlevel 3 goto GPUCLI
if errorlevel 2 goto CPUSERVER
goto GPUSERVER

:CHECKMODEL
if not exist "%MODEL%" (
  echo [ERROR] Model not found:
  echo %MODEL%
  pause
  goto MENU
)
exit /b 0

:GPUSERVER
call :CHECKMODEL
if not exist "%GPU_SERVER%" (
  echo [ERROR] GPU llama-server.exe not found:
  echo %GPU_SERVER%
  pause
  goto MENU
)
start "%NAME% GPU Server" /D "%GPU%" "%GPU_SERVER%" -m "%MODEL%" -c 16384 --jinja --alias "%NAME%"
echo Server process started on http://127.0.0.1:8080
echo Verify /health before connecting clients.
pause
goto MENU

:CPUSERVER
call :CHECKMODEL
if not exist "%CPU_SERVER%" (
  echo [ERROR] CPU llama-server.exe not found:
  echo %CPU_SERVER%
  pause
  goto MENU
)
start "%NAME% CPU Server" /D "%CPU%" "%CPU_SERVER%" -m "%MODEL%" -c 16384 --jinja --alias "%NAME%"
echo Server process started on http://127.0.0.1:8080
echo Verify /health before connecting clients.
pause
goto MENU

:GPUCLI
call :CHECKMODEL
if not exist "%GPU_CLI%" (
  echo [ERROR] GPU llama-cli.exe not found:
  echo %GPU_CLI%
  pause
  goto MENU
)
pushd "%GPU%"
"%GPU_CLI%" -m "%MODEL%" --jinja
popd
pause
goto MENU

:CPUCLI
call :CHECKMODEL
if not exist "%CPU_CLI%" (
  echo [ERROR] CPU llama-cli.exe not found:
  echo %CPU_CLI%
  pause
  goto MENU
)
pushd "%CPU%"
"%CPU_CLI%" -m "%MODEL%" --jinja
popd
pause
goto MENU
