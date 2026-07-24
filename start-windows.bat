@echo off
REM VoxStudio - double-click launcher for Windows.
REM Double-click this file. It sets up everything the first time (this takes a
REM while and downloads a few gigabytes), then just launches after that.
REM Nothing here is dangerous and nothing leaves your PC.

setlocal enabledelayedexpansion
cd /d "%~dp0"
title VoxStudio local voice cloner

echo.
echo === VoxStudio local voice cloner - starting up ===
echo.

REM --- Python 3.11 (Coqui XTTS needs Python 3.9-3.11) ---
set "PY="
py -3.11 --version >nul 2>&1 && set "PY=py -3.11"
if not defined PY ( py -3.10 --version >nul 2>&1 && set "PY=py -3.10" )
if not defined PY ( python --version >nul 2>&1 && set "PY=python" )
if not defined PY (
  echo Trying to install Python 3.11 via winget...
  winget install -e --id Python.Python.3.11 --accept-source-agreements --accept-package-agreements
  py -3.11 --version >nul 2>&1 && set "PY=py -3.11"
)
if not defined PY (
  echo.
  echo Could not find or install Python. Please install Python 3.11 from
  echo https://www.python.org/downloads/  ^(tick "Add python.exe to PATH"^),
  echo then double-click this file again.
  pause
  exit /b 1
)
echo Found Python: %PY%

REM --- ffmpeg (needed to read your audio samples) ---
where ffmpeg >nul 2>&1
if errorlevel 1 (
  echo Installing ffmpeg via winget...
  winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
  where ffmpeg >nul 2>&1
  if errorlevel 1 (
    echo.
    echo ffmpeg was installed but this window can't see it yet.
    echo Please CLOSE this window and double-click start-windows.bat again.
    pause
    exit /b 1
  )
)
echo Found ffmpeg.

REM --- Virtual environment + dependencies (first run only) ---
if not exist ".venv\" (
  echo Creating a private Python environment...
  %PY% -m venv .venv || ( echo Could not create the environment. & pause & exit /b 1 )
)
set "VPY=.venv\Scripts\python.exe"
if not exist ".venv\.installed" (
  echo Installing the voice engine - this downloads a few GB and can take several minutes...
  "%VPY%" -m pip install --upgrade pip >nul 2>&1
  "%VPY%" -m pip install -r requirements.txt || ( echo Installing dependencies failed. Scroll up for the error. & pause & exit /b 1 )
  echo done> ".venv\.installed"
  echo Voice engine installed.
) else (
  echo Voice engine already installed.
)

REM --- Start the server if not already running ---
curl -s http://127.0.0.1:8000/ >nul 2>&1
if errorlevel 1 (
  echo Starting the voice server...
  start "VoxStudio server" /min "%VPY%" server.py
  set /a tries=0
  :waitloop
  timeout /t 1 /nobreak >nul
  curl -s http://127.0.0.1:8000/ >nul 2>&1
  if not errorlevel 1 goto serverup
  set /a tries+=1
  if !tries! lss 40 goto waitloop
  echo The server didn't start. See voxstudio-server.log for details.
  pause
  exit /b 1
  :serverup
  echo Voice server running at http://127.0.0.1:8000
) else (
  echo Voice server already running.
)

REM --- Open the studio ---
start "" index.html

echo.
echo VoxStudio is open in your browser.
echo.
echo Next, in the page:
echo   1. Choose "Local - no API", then click Connect.
echo   2. Under "Clone a voice", give it a name, add a short clean sample
echo      ^(upload a file or record from your mic^), tick the consent box,
echo      and click "Create voice clone".
echo   3. Type some text, pick a language, and click "Generate speech".
echo.
echo The very first "Generate" downloads the voice model (~1.8 GB) once - after
echo that it works offline. To stop the server later, double-click stop-windows.bat.
echo.
pause
