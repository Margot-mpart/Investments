#!/bin/bash
# VoxStudio — stops the local voice server. Double-click to run.
cd "$(dirname "$0")" || exit 1
if pgrep -f "server.py" >/dev/null 2>&1; then
  pkill -f "server.py"
  printf "\033[1;32m✓ VoxStudio voice server stopped.\033[0m\n"
else
  printf "VoxStudio voice server wasn't running.\n"
fi
printf "\nPress any key to close this window."
read -r -n 1
