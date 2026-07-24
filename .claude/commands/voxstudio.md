---
description: Install, launch, and run the VoxStudio local voice cloner (Coqui XTTS-v2) on this machine
argument-hint: "[start | stop | status | clone]"
allowed-tools: Bash, Read, Write, Edit, Glob
---

You are Claude Code running on the **user's own computer**, so you can install
software, run processes, and open apps for them. Your job is to get the
**VoxStudio local voice engine** — the open-source Coqui XTTS-v2 model wrapped
by `server.py` — installed and running, and open the `index.html` studio in the
browser so the user can clone voices and generate speech entirely offline, with
no API key.

The requested action is: **$ARGUMENTS** (empty means `start`).

Work autonomously: run the steps, adapt commands to the user's OS, and only stop
to ask the user when a step genuinely needs their decision (e.g. installing a
system package manager, or a destructive choice). Report what you did in plain
language at the end. Never expose or ask for any API key — this engine doesn't
use one.

---

## First, orient yourself

1. **Find the project.** Look for `server.py` and `index.html` in the current
   directory (and one level down). If found, use that folder as `$PROJECT`.
   If not found, ask the user where they cloned the repo, or offer to clone it:
   `git clone https://github.com/Margot-mpart/Investments.git` then
   `git checkout claude/eleven-labs-voice-clone-956rm4`.
2. **Detect the OS** (`uname` on macOS/Linux; you are on Windows if that fails
   or `$OS` is `Windows_NT`). All commands below have per-OS variants — pick the
   matching one.

---

## Action: `start` (default — full setup, then launch)

### 1. Python
Confirm Python 3.10 or 3.11 is available (Coqui XTTS supports 3.9–3.11; 3.11 is
the safest). Try `python3 --version` (macOS/Linux) or `py -3.11 --version` /
`python --version` (Windows).
- If missing or too new/old, tell the user how to get 3.11:
  - macOS: `brew install python@3.11`
  - Ubuntu/Debian: `sudo apt install python3.11 python3.11-venv`
  - Windows: install from python.org or `winget install Python.Python.3.11`

### 2. ffmpeg (required to decode uploaded audio)
Check with `ffmpeg -version`. If missing, install it:
- macOS: `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt update && sudo apt install -y ffmpeg`
- Fedora: `sudo dnf install -y ffmpeg`
- Windows: `choco install ffmpeg` **or** `winget install Gyan.FFmpeg`
If no package manager is present, point them to https://ffmpeg.org/download.html
and pause until they confirm it's installed and on `PATH`.

### 3. Virtual environment + dependencies
Create an isolated env inside `$PROJECT` so nothing pollutes system Python:
- macOS/Linux:
  ```bash
  cd "$PROJECT"
  python3.11 -m venv .venv
  ./.venv/bin/python -m pip install --upgrade pip
  ./.venv/bin/python -m pip install -r requirements.txt
  ```
- Windows (PowerShell):
  ```powershell
  cd $PROJECT
  py -3.11 -m venv .venv
  .\.venv\Scripts\python -m pip install --upgrade pip
  .\.venv\Scripts\python -m pip install -r requirements.txt
  ```
This pulls in PyTorch and Coqui TTS and can take several minutes and a few GB of
disk — tell the user it's expected, and let it run to completion. If PyTorch
fails to install, report the exact error; it's usually a Python-version issue
(fall back to 3.11).

### 4. Launch the server
Start it in the background and keep the log:
- macOS/Linux:
  ```bash
  cd "$PROJECT"
  nohup ./.venv/bin/python server.py > voxstudio-server.log 2>&1 &
  ```
- Windows (PowerShell):
  ```powershell
  Start-Process -WindowStyle Hidden -FilePath .\.venv\Scripts\python -ArgumentList server.py -RedirectStandardOutput voxstudio-server.log -RedirectStandardError voxstudio-server.err
  ```
Then poll until it answers (up to ~30s): `curl -s http://127.0.0.1:8000/`
should return JSON with `"status":"ok"`. If it never comes up, show the last
20 lines of `voxstudio-server.log`.

### 5. Open the studio
Open `index.html` in the default browser:
- macOS: `open index.html`
- Linux: `xdg-open index.html`
- Windows: `start index.html`

### 6. Tell the user how to finish (do NOT try to click for them)
In the page: pick **Local · no API** → click **Connect** (URL is already
`http://127.0.0.1:8000`) → in **Clone a voice (local)** give it a name, add a
short clean sample (upload a file or record from the mic), tick the consent box,
click **Create voice clone**. Then type text, choose a **Speech language**, and
hit **Generate speech**.

Note the first **Generate** downloads the XTTS-v2 model (~1.8 GB) once and
caches it; after that it works fully offline. A GPU makes it fast; CPU works but
is slower.

---

## Action: `status`
Report whether the server is up: `curl -s http://127.0.0.1:8000/` (show the
voice count it returns), and whether `.venv` exists. On macOS/Linux also show
the process: `pgrep -fa server.py`.

## Action: `stop`
Stop the background server.
- macOS/Linux: `pkill -f "server.py"` (or kill the PID from `pgrep -f server.py`).
- Windows: find it with `Get-CimInstance Win32_Process -Filter "CommandLine like '%server.py%'"` and stop it with `Stop-Process -Id <pid>`.
Confirm `curl http://127.0.0.1:8000/` no longer responds.

## Action: `clone`
Assume the server is already running (run `start`'s steps 4–5 first if not).
Then walk the user through the in-app cloning flow from step 6 above. You cannot
click inside their browser, so give clear, numbered guidance and offer to
troubleshoot any error shown in the app or the server log.

---

## Guardrails
- The server binds to `127.0.0.1` only — keep it local; do not expose it to the
  network or the internet.
- Voice cloning can convincingly imitate a real person. Remind the user to clone
  only their own voice or a voice they have the speaker's explicit permission to
  use. Do not help configure it for impersonation or deception.
- Everything stays on the user's machine — samples live in `$PROJECT/voices/`
  and no audio is uploaded anywhere.
