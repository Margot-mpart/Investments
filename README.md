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

## Two speech engines

**Browser voices (default).** Uses the Web Speech API built into Chrome,
Edge, Safari, and Firefox. Works immediately with no account or API key.
Sliders control speed, pitch, and volume. Playback is live synthesis, so
there is no downloadable file in this mode.

**ElevenLabs API.** Switch the toggle in the header, paste your own
ElevenLabs API key, and hit Connect. The app then:

- loads your real ElevenLabs voice library (with accent/gender/age labels),
- lets you pick a model (Multilingual v2, Turbo v2.5, or Flash v2.5),
- exposes the real voice settings — stability, similarity, style exaggeration,
- generates MP3 audio you can play, replay from history, and download.

Your API key stays in the browser tab and is sent only to
`api.elevenlabs.io` — there is no backend.

## Voice cloning

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
- Searchable voice list with generated avatars
- Animated waveform while audio plays
- History of the last 10 ElevenLabs generations with replay and download
- Responsive layout (sidebar stacks below the editor on narrow screens)
- Zero dependencies — one self-contained `index.html`
