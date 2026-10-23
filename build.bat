@echo off
rem Builds the EwE release .exe into dist\EwE\ (requires uv)
setlocal
cd /d %~dp0

if not exist .build-venv\Scripts\python.exe (
    echo [EwE build] Creating build environment...
    uv venv .build-venv --python 3.12
    uv pip install -p .build-venv -r requirements.txt pyinstaller
)

echo [EwE build] Building EwE...
.build-venv\Scripts\pyinstaller.exe EwE.spec --noconfirm

if %errorlevel% neq 0 (
    echo [EwE build] FAILED
    exit /b 1
)

echo.
echo [EwE build] Done. Single-file release: dist\EwE.exe
