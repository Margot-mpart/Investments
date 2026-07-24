@echo off
REM VoxStudio - one-click upgrade to the VoxCPM engine (Windows, NVIDIA GPU).
REM Double-click AFTER you've run start-windows.bat at least once. It adds the
REM higher-quality VoxCPM2 model (48 kHz, 30 languages, Apache-2.0). The server
REM then uses VoxCPM automatically whenever an NVIDIA GPU is present, and falls
REM back to the original engine otherwise. Nothing here is destructive.

setlocal
cd /d "%~dp0"
title VoxStudio - VoxCPM upgrade

echo.
echo === Upgrading VoxStudio to the VoxCPM engine ===
echo.

if not exist ".venv\Scripts\python.exe" (
  echo Please run start-windows.bat first to set up the app, then run this again.
  pause
  exit /b 1
)
set "VPY=.venv\Scripts\python.exe"

REM --- Check for an NVIDIA GPU ---
where nvidia-smi >nul 2>&1
if errorlevel 1 (
  echo No NVIDIA GPU was detected. VoxCPM needs an NVIDIA card with about 8 GB
  echo of VRAM, so it would not run on this machine. Keeping the current engine.
  pause
  exit /b 1
)
echo NVIDIA GPU detected.
echo.
echo Installing VoxCPM - this downloads several GB and can take a while...
"%VPY%" -m pip install -r requirements-voxcpm.txt
if errorlevel 1 (
  echo.
  echo VoxCPM installation failed. Your existing setup is unchanged and still
  echo works. Scroll up for the error, or ask Claude Code with /voxstudio.
  pause
  exit /b 1
)

echo.
echo Done. VoxCPM is installed.
echo Restart the voice server for it to take effect:
echo   1. Double-click stop-windows.bat
echo   2. Double-click start-windows.bat
echo When you click Connect in the app, the status line will read "VoxCPM2 (48 kHz)".
echo.
pause
