@echo off
setlocal
title Pocket AI - OpenCode (Windows)

set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"

set "NODE_HOME=%ROOT%\AI\node"
set "OPENCODE_HOME=%ROOT%\AI\OpenCode"
set "OPENCODE_CONFIG=%ROOT%\AI\config\opencode.json"

if not exist "%OPENCODE_HOME%\opencode.cmd" (
  echo [ERROR] OpenCode not found:
  echo %OPENCODE_HOME%\opencode.cmd
  pause
  exit /b 1
)

if exist "%NODE_HOME%" set "PATH=%NODE_HOME%;%PATH%"
if exist "%OPENCODE_HOME%" set "PATH=%OPENCODE_HOME%;%PATH%"

echo Starting OpenCode...
echo Config: %OPENCODE_CONFIG%
call "%OPENCODE_HOME%\opencode.cmd"

endlocal
