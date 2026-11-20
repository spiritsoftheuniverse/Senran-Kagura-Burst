@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist "SOURCE_MANIFEST.json" (
  echo ERROR: Sources missing. Run FETCH_SOURCES.bat first.
  exit /b 1
)
call "%~dp0VERIFY_SOURCES.bat"
if errorlevel 1 exit /b 1
where cargo >nul 2>&1
if errorlevel 1 (
  echo ERROR: Rust Cargo is not in PATH. Install/update Rust stable ^(Zakuro requires Rust 1.95+^).
  exit /b 1
)
echo === Building local 3dsrecomp ===
cargo build --release --manifest-path "external\3dsrecomp\Cargo.toml"
if errorlevel 1 exit /b 1
echo === Building local Zakuro ===
cargo build --release --manifest-path "external\zakuro\Cargo.toml" -p zakuro
if errorlevel 1 exit /b 1
echo PASS: Both local tools built. No game was recompiled.
exit /b 0
