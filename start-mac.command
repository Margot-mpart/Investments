#!/bin/bash
# VoxStudio — double-click launcher for macOS.
# Double-click this file in Finder. It sets up everything the first time
# (this takes a while and downloads a few gigabytes), then just launches on
# every run after that. Nothing here is dangerous and nothing leaves your Mac.

set -u
cd "$(dirname "$0")" || exit 1

say()  { printf "\n\033[1;35m%s\033[0m\n" "$1"; }
ok()   { printf "\033[1;32m✓ %s\033[0m\n" "$1"; }
warn() { printf "\033[1;33m! %s\033[0m\n" "$1"; }
die()  { printf "\n\033[1;31m✗ %s\033[0m\n" "$1"; printf "\nPress any key to close this window."; read -r -n 1; exit 1; }

say "VoxStudio local voice cloner — starting up"

# --- Homebrew (used to install Python/ffmpeg if they're missing) ---
BREW=""
if command -v brew >/dev/null 2>&1; then BREW="brew"; fi

# --- Python 3.11 (Coqui XTTS needs Python 3.9–3.11) ---
PY=""
for c in python3.11 python3.10 python3; do
  if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
  if [ -n "$BREW" ]; then
    say "Installing Python 3.11 (via Homebrew)…"; brew install python@3.11 && PY="python3.11"
  fi
fi
[ -z "$PY" ] && die "Python isn't installed. Install it from https://www.python.org/downloads/ (get 3.11), then double-click this file again."
PYVER="$("$PY" -c 'import sys;print("%d.%d"%sys.version_info[:2])' 2>/dev/null)"
case "$PYVER" in
  3.9|3.10|3.11) ok "Python $PYVER" ;;
  *) warn "Python $PYVER may be too new for the voice model; trying anyway. If setup fails, install Python 3.11." ;;
esac

# --- ffmpeg (needed to read your audio samples) ---
if command -v ffmpeg >/dev/null 2>&1; then
  ok "ffmpeg"
elif [ -n "$BREW" ]; then
  say "Installing ffmpeg (via Homebrew)…"; brew install ffmpeg || die "Couldn't install ffmpeg. Run 'brew install ffmpeg' in Terminal, then try again."
  ok "ffmpeg installed"
else
  die "ffmpeg isn't installed and Homebrew isn't available. Install Homebrew from https://brew.sh then double-click this file again."
fi

# --- Virtual environment + dependencies (first run only) ---
if [ ! -d ".venv" ]; then
  say "Creating a private Python environment…"; "$PY" -m venv .venv || die "Could not create the environment."
fi
VPY="./.venv/bin/python"
if [ ! -f ".venv/.installed" ]; then
  say "Installing the voice engine — this downloads a few GB and can take several minutes…"
  "$VPY" -m pip install --upgrade pip >/dev/null 2>&1
  "$VPY" -m pip install -r requirements.txt || die "Installing dependencies failed. Scroll up for the error."
  touch ".venv/.installed"
  ok "Voice engine installed"
else
  ok "Voice engine already installed"
fi

# --- Start the server if it isn't already running ---
if curl -s http://127.0.0.1:8000/ >/dev/null 2>&1; then
  ok "Voice server already running"
else
  say "Starting the voice server…"
  nohup "$VPY" server.py > voxstudio-server.log 2>&1 &
  for _ in $(seq 1 40); do
    sleep 1
    curl -s http://127.0.0.1:8000/ >/dev/null 2>&1 && break
  done
  curl -s http://127.0.0.1:8000/ >/dev/null 2>&1 || die "The server didn't start. See voxstudio-server.log for details."
  ok "Voice server running at http://127.0.0.1:8000"
fi

# --- Open the studio in the browser ---
open index.html
say "VoxStudio is open in your browser."
cat <<'TIP'

Next, in the page:
  1. Choose "Local · no API", then click Connect.
  2. Under "Clone a voice", give it a name, add a short clean sample
     (upload a file or record from your mic), tick the consent box,
     and click "Create voice clone".
  3. Type some text, pick a language, and click "Generate speech".

The very first "Generate" downloads the voice model (~1.8 GB) once — after
that it works offline. You can close this window; leave it open if you want
to keep the server running. To stop the server later, double-click
"stop-mac.command".
TIP
printf "\nPress any key to close this window."
read -r -n 1
