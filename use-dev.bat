@echo off
set "ROOT=%~dp0"
set "PATH=%ROOT%Python;%ROOT%Python\Scripts;%ROOT%dotnet;%PATH%"
set "DOTNET_ROOT=%ROOT%dotnet"
cmd /k