# VoxStudio — AI Voice Generator

An ElevenLabs-style text-to-speech studio in a single HTML file. Dark studio UI
with a text editor, searchable voice picker, tuning sliders, an animated
playback bar, and a generation history.

## Running it

No build step and no server required — just open the file:

```
open index.html        # macOS
xdg-open index.html    # Linux
```

or serve it locally (needed in some browsers for the ElevenLabs engine):

```
python3 -m http.server 8000
# then visit http://localhost:8000
```

## Three speech engines

**Browser voices (default).** Uses the Web Speech API built into Chrome,
Edge, Safari, and Firefox. Works immediately with no account or API key.
Sliders control speed, pitch, and volume. Playback is live synthesis, so
there is no downloadable file in this mode.

**Local · no API.** Runs the open-source **Coqui XTTS-v2** model on your own
machine for voice cloning and speech — no account, no API key, no per-use
cost, and nothing leaves your computer. Requires the bundled Python server
(see [Local voice engine](#local-voice-engine-no-api) below).

**ElevenLabs API.** Switch the toggle in the header, paste your own
ElevenLabs API key, and hit Connect. The app then:

- loads your real ElevenLabs voice library (with accent/gender/age labels),
- lets you pick a model (Multilingual v2, Turbo v2.5, or Flash v2.5),
- exposes the real voice settings — stability, similarity, style exaggeration,
- generates MP3 audio you can play, replay from history, and download.

Your API key stays in the browser tab and is sent only to
`api.elevenlabs.io` — there is no backend.

## Local voice engine (no API)

The **Local · no API** engine does voice cloning and text-to-speech entirely
on your own machine using the open-source [Coqui XTTS-v2](https://github.com/idiap/coqui-ai-TTS)
model. No account, no API key, no per-use cost, and no audio ever leaves your
computer.

### Easiest: let Claude Code do it

This repo ships a Claude Code slash command at
[`.claude/commands/voxstudio.md`](.claude/commands/voxstudio.md). Open this
project folder in Claude Code (the terminal CLI or the Claude desktop app), then
run:

```
/voxstudio
```

Claude Code will detect your OS, install ffmpeg and the Python dependencies into
a local virtual environment, start the server, and open the studio — the whole
setup, hands-off. Other actions: `/voxstudio status`, `/voxstudio stop`,
`/voxstudio clone`. (The command is project-scoped, so it appears automatically
when this folder is open; you can also copy the file into `~/.claude/commands/`
to make it available everywhere.)

### Or set it up manually

### 1. Start the server

```bash
pip install -r requirements.txt   # installs coqui-tts, fastapi, uvicorn, pydub…
python server.py                  # serves on http://127.0.0.1:8000
```

You also need **ffmpeg** installed on your system (used to decode uploaded
audio) — e.g. `brew install ffmpeg`, `apt install ffmpeg`, or
`choco install ffmpeg`. The first synthesis downloads the model (~1.8 GB) and
caches it. A GPU is optional but makes synthesis much faster; CPU works but is
slow.

### 2. Use it in the app

1. Open `index.html` and pick the **Local · no API** engine.
2. Click **Connect** (default URL `http://127.0.0.1:8000`).
3. In **Clone a voice (local)**, name the voice, add a short clean sample
   (upload files or record from your mic), tick the consent box, and hit
   **Create voice clone**.
4. The clone appears in the voice list with a `CLONE` badge and is
   auto-selected. Type text, hit **Generate speech**, and you'll hear it — and
   can download the WAV.

### Language

XTTS-v2 is multilingual. The **Speech language** card lets you pick from 17
languages (English, Spanish, French, German, Italian, Portuguese, Polish,
Turkish, Russian, Dutch, Czech, Arabic, Chinese, Hungarian, Korean, Japanese,
Hindi). A cloned voice can speak any of them, regardless of the language it was
sampled in — clone an English sample and have it read Japanese in the same
voice.

### Managing voices

Hover any cloned voice in the list and click the 🗑 icon to delete it. This
calls the server's `DELETE /v1/voices/{voice_id}` endpoint and removes the
stored reference clip from `./voices/`. (Deleting works for ElevenLabs clones
too, via the same button.)

Cloning here is *zero-shot*: your samples are stored locally under `./voices/`
as a reference clip, and XTTS-v2 conditions on that clip at synthesis time.
Nothing is uploaded and no model is fine-tuned.

**How the server talks to the app.** `server.py` exposes an
ElevenLabs-compatible subset (`GET /v1/voices`, `POST /v1/voices/add`,
`POST /v1/text-to-speech/{voice_id}`, `DELETE /v1/voices/{voice_id}`), so the
same front-end drives either the local model or the hosted API.

## Voice cloning with ElevenLabs

With the ElevenLabs engine connected, the **Clone a voice** panel creates an
instant voice clone from your own samples:

1. Name the voice.
2. Add 1–2 minutes of clean speech — drag-and-drop audio files (mp3, wav,
   m4a, webm; up to 25 samples) or hit **Record sample** to capture audio
   straight from your microphone.
3. Confirm the consent checkbox — clone only your own voice or a voice you
   have explicit permission to use.
4. **Create voice clone** uploads the samples to the ElevenLabs
   `/v1/voices/add` endpoint. The new voice appears in your voice list with
   a `CLONE` badge, is auto-selected, and works with every model and
   setting like any other voice.

Notes: instant voice cloning requires a paid ElevenLabs plan (Starter or
above), and cloned voices live in your ElevenLabs account — this app holds
no copies. Use of cloned voices is subject to the ElevenLabs terms of use
and applicable law.

## Features

- 5,000-character editor with live character count
- Searchable voice list with generated avatars and `CLONE` badges
- Animated waveform while audio plays
- History of the last 10 generations with replay and download
- Responsive layout (sidebar stacks below the editor on narrow screens)
- Front-end is one self-contained `index.html` with zero dependencies

## Responsible use

Voice cloning can convincingly imitate a real person. Only clone your own
voice, or a voice you have the speaker's explicit permission to use. Do not use
it to impersonate people, to deceive, or for any purpose that violates
applicable law or the terms of the engine you use. The consent checkbox in the
cloning panel is a reminder of this, not a substitute for actual consent.
