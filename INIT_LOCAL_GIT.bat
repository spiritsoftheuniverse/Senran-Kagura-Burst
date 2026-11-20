@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if exist ".git" (
  echo This folder is already a Git repository.
  exit /b 1
)
where git >nul 2>&1
if errorlevel 1 (
  echo ERROR: Git is not on PATH.
  exit /b 1
)
git init -b main
if errorlevel 1 exit /b 1
echo Independent local Git repository initialized. No remote configured. No commit or push performed.
git remote -v
exit /b 0
