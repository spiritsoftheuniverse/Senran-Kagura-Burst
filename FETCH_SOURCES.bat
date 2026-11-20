@echo off
setlocal EnableExtensions
cd /d "%~dp0"
where py >nul 2>&1
if not errorlevel 1 (
    py -3 "%~dp0scripts\fetch_sources.py"
) else (
    python "%~dp0scripts\fetch_sources.py"
)
exit /b %ERRORLEVEL%
