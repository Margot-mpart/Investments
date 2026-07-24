"""
VoxStudio local voice engine — self-hosted, no API key, no per-use cost.

Wraps the open-source Coqui XTTS-v2 model to do zero-shot voice cloning and
text-to-speech entirely on your own machine. The HTTP surface deliberately
mirrors the subset of the ElevenLabs API that the VoxStudio front-end uses, so
the same UI drives either engine:

    GET  /v1/voices                       -> { "voices": [ ... ] }
    POST /v1/voices/add   (multipart)     -> { "voice_id": "..." }
    POST /v1/text-to-speech/{voice_id}    -> audio/wav bytes
    DELETE /v1/voices/{voice_id}          -> { "ok": true }

Cloning is zero-shot: uploaded samples are concatenated into a single reference
clip and stored under ./voices/. At synthesis time XTTS-v2 conditions on that
clip — nothing is uploaded anywhere, and no model is fine-tuned.

Run it:
    pip install -r requirements.txt
    python server.py            # serves on http://127.0.0.1:8000

Only clone your own voice, or a voice you have explicit permission to use.
"""

import io
import json
import os
import uuid
import wave

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

# Accept the Coqui model license non-interactively (CPML, non-commercial).
os.environ.setdefault("COQUI_TOS_AGREED", "1")

VOICES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voices")
os.makedirs(VOICES_DIR, exist_ok=True)

MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"
DEFAULT_LANGUAGE = os.environ.get("VOXSTUDIO_LANG", "en")

app = FastAPI(title="VoxStudio local voice engine")

# The front-end is a static file (file:// or any localhost port), so allow any
# origin — this server only ever binds to localhost.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Lazy model loading — the first request pays the (large) load cost, not import.
# ---------------------------------------------------------------------------
_tts = None


def get_tts():
    global _tts
    if _tts is None:
        import torch
        from TTS.api import TTS

        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[voxstudio] loading {MODEL_NAME} on {device} (first run downloads ~1.8 GB)…")
        _tts = TTS(MODEL_NAME).to(device)
        print("[voxstudio] model ready.")
    return _tts


# ---------------------------------------------------------------------------
# Voice metadata storage — one folder per voice: reference.wav + meta.json
# ---------------------------------------------------------------------------
def _voice_dir(voice_id: str) -> str:
    return os.path.join(VOICES_DIR, voice_id)


def _read_meta(voice_id: str):
    path = os.path.join(_voice_dir(voice_id), "meta.json")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def list_voices():
    voices = []
    for voice_id in sorted(os.listdir(VOICES_DIR)):
        meta = _read_meta(voice_id)
        if meta:
            voices.append(meta)
    return voices


# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------
def _decode_to_wav(raw: bytes, dest_path: str):
    """Decode arbitrary uploaded audio to a 22.05 kHz mono wav using pydub."""
    from pydub import AudioSegment

    seg = AudioSegment.from_file(io.BytesIO(raw))
    seg = seg.set_channels(1).set_frame_rate(22050)
    seg.export(dest_path, format="wav")


def _floats_to_wav_bytes(samples, sample_rate: int) -> bytes:
    """Pack a list of float samples in [-1, 1] into 16-bit PCM wav bytes."""
    import numpy as np

    arr = np.asarray(samples, dtype=np.float32)
    arr = np.clip(arr, -1.0, 1.0)
    pcm = (arr * 32767.0).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/v1/voices")
def get_voices():
    return {"voices": list_voices()}


@app.post("/v1/voices/add")
async def add_voice(
    name: str = Form(...),
    description: str = Form(""),
    files: list[UploadFile] = File(...),
):
    if not files:
        raise HTTPException(status_code=400, detail="At least one audio sample is required.")

    voice_id = "local_" + uuid.uuid4().hex[:12]
    vdir = _voice_dir(voice_id)
    os.makedirs(vdir, exist_ok=True)

    # Concatenate every uploaded sample into one reference clip for XTTS.
    from pydub import AudioSegment

    combined = AudioSegment.empty()
    for upload in files:
        raw = await upload.read()
        if not raw:
            continue
        try:
            seg = AudioSegment.from_file(io.BytesIO(raw))
        except Exception as exc:  # noqa: BLE001 - surface a clean client error
            raise HTTPException(
                status_code=400,
                detail=f"Could not decode '{upload.filename}': {exc}. Is ffmpeg installed?",
            )
        combined += seg.set_channels(1).set_frame_rate(22050)

    if len(combined) == 0:
        raise HTTPException(status_code=400, detail="Uploaded samples contained no audio.")

    ref_path = os.path.join(vdir, "reference.wav")
    combined.export(ref_path, format="wav")

    meta = {
        "voice_id": voice_id,
        "name": name,
        "category": "cloned",
        "description": description,
        "labels": {"engine": "xtts-v2"},
    }
    with open(os.path.join(vdir, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh)

    return {"voice_id": voice_id}


class TTSRequest(BaseModel):
    text: str
    language: str | None = None
    # Accepted and ignored for ElevenLabs request-shape compatibility:
    model_id: str | None = None
    voice_settings: dict | None = None


@app.post("/v1/text-to-speech/{voice_id}")
def text_to_speech(voice_id: str, req: TTSRequest):
    meta = _read_meta(voice_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Voice not found.")
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="No text provided.")

    ref_path = os.path.join(_voice_dir(voice_id), "reference.wav")
    if not os.path.isfile(ref_path):
        raise HTTPException(status_code=404, detail="Voice reference audio is missing.")

    tts = get_tts()
    try:
        wav = tts.tts(
            text=req.text,
            speaker_wav=ref_path,
            language=req.language or DEFAULT_LANGUAGE,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {exc}")

    sample_rate = getattr(getattr(tts, "synthesizer", None), "output_sample_rate", 24000)
    audio_bytes = _floats_to_wav_bytes(wav, sample_rate)
    return Response(content=audio_bytes, media_type="audio/wav")


@app.delete("/v1/voices/{voice_id}")
def delete_voice(voice_id: str):
    import shutil

    vdir = _voice_dir(voice_id)
    if not os.path.isdir(vdir):
        raise HTTPException(status_code=404, detail="Voice not found.")
    shutil.rmtree(vdir)
    return {"ok": True}


@app.get("/")
def root():
    return {"status": "ok", "voices": len(list_voices()), "model": MODEL_NAME}


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("VOXSTUDIO_HOST", "127.0.0.1")
    port = int(os.environ.get("VOXSTUDIO_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
