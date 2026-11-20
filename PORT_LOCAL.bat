@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if "%~1"=="" (
  echo Usage: PORT_LOCAL.bat "full path to your own decrypted Burst.3ds"
  exit /b 2
)
set "ROM=%~f1"
if not exist "%ROM%" (
  echo ERROR: Game file not found: "%ROM%"
  exit /b 1
)
set "TOOL=%~dp0external\3dsrecomp\target\release\3dsrecomp.exe"
if not exist "%TOOL%" (
  echo ERROR: Recompiler not built. Run BUILD_TOOLS.bat first.
  exit /b 1
)
if exist "local\ports\Burst" (
  echo ERROR: A Burst port already exists. Refusing to overwrite its generated files.
  exit /b 1
)
if not exist "local\ports" mkdir "local\ports"
"%TOOL%" port "%ROM%" "%~dp0local\ports\Burst" --name Burst --zakuro "%~dp0external\zakuro"
exit /b %ERRORLEVEL%
