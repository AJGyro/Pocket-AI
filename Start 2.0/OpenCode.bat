@echo off
setlocal

REM Find pendrive root
set "USB=%~dp0.."
for %%I in ("%USB%") do set "USB=%%~fI"

REM Portable Node + OpenCode
set "NODE_HOME=%USB%\AI\node"
set "OPENCODE_HOME=%USB%\AI\OpenCode"
set "OPENCODE_CONFIG=%USB%\AI\config\opencode.json"

REM Use portable Node/OpenCode
set "PATH=%NODE_HOME%;%OPENCODE_HOME%;%PATH%"

REM Launch OpenCode directly
call "%OPENCODE_HOME%\opencode.cmd"

endlocal

