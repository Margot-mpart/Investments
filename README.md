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

## Features

- 5,000-character editor with live character count
- Searchable voice list with generated avatars
- Animated waveform while audio plays
- History of the last 10 ElevenLabs generations with replay and download
- Responsive layout (sidebar stacks below the editor on narrow screens)
- Zero dependencies — one self-contained `index.html`
