@echo off
REM VoxStudio - stops the local voice server. Double-click to run.
setlocal
title Stop VoxStudio
set "stopped="
for /f "tokens=2 delims==; " %%p in ('wmic process where "commandline like '%%server.py%%' and name like '%%python%%'" get processid /value 2^>nul ^| find "="') do (
  taskkill /PID %%p /F >nul 2>&1 && set "stopped=1"
)
if defined stopped (
  echo VoxStudio voice server stopped.
) else (
  echo VoxStudio voice server wasn't running.
)
pause
