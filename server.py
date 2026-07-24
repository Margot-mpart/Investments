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

XTTS_MODEL = "tts_models/multilingual/multi-dataset/xtts_v2"
VOXCPM_MODEL = os.environ.get("VOXCPM_MODEL", "openbmb/VoxCPM2")
DEFAULT_LANGUAGE = os.environ.get("VOXSTUDIO_LANG", "en")

# Which synthesis engine to use:
#   "auto"   (default) -> VoxCPM if an NVIDIA GPU and the voxcpm package are
#                         both available, otherwise Coqui XTTS-v2 (CPU-capable).
#   "voxcpm" / "xtts"  -> force one.
ENGINE_PREF = os.environ.get("VOXSTUDIO_ENGINE", "auto").lower()

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
# Engine selection + lazy loading.
#
# Both engines clone zero-shot: reference clip + text -> audio. They are wrapped
# behind a single `synth(text, reference_wav, language) -> (samples, sample_rate)`
# callable so the rest of the server (and the whole front-end) is engine-agnostic.
# The first synthesis request pays the (large) model-load cost, not import.
# ---------------------------------------------------------------------------
def _cuda_available() -> bool:
    try:
        import torch

        return bool(torch.cuda.is_available())
    except Exception:
        return False


def _voxcpm_importable() -> bool:
    import importlib.util

    return importlib.util.find_spec("voxcpm") is not None


def selected_engine() -> str:
    """Resolve which engine will be used — cheap, does not load any model."""
    if ENGINE_PREF in ("voxcpm", "xtts"):
        return ENGINE_PREF
    if _cuda_available() and _voxcpm_importable():
        return "voxcpm"
    return "xtts"


def engine_model_id(name: str) -> str:
    return VOXCPM_MODEL if name == "voxcpm" else XTTS_MODEL


_engine = None  # {"name": str, "synth": callable, "model": str}


def get_engine():
    global _engine
    if _engine is not None:
        return _engine

    name = selected_engine()

    if name == "voxcpm":
        from voxcpm import VoxCPM

        print(f"[voxstudio] loading VoxCPM ({VOXCPM_MODEL}) on GPU (first run downloads the model)…")
        model = VoxCPM.from_pretrained(VOXCPM_MODEL, load_denoiser=False)
        sample_rate = int(getattr(getattr(model, "tts_model", None), "sample_rate", 48000))

        def synth(text, reference_wav, language=None):
            # VoxCPM detects language from the text itself; `language` is ignored.
            wav = model.generate(text=text, reference_wav_path=reference_wav)
            return wav, sample_rate

        _engine = {"name": "voxcpm", "synth": synth, "model": VOXCPM_MODEL}
    else:
        import torch
        from TTS.api import TTS

        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[voxstudio] loading Coqui XTTS-v2 on {device} (first run downloads ~1.8 GB)…")
        tts = TTS(XTTS_MODEL).to(device)
        sample_rate = int(getattr(getattr(tts, "synthesizer", None), "output_sample_rate", 24000))

        def synth(text, reference_wav, language=None):
            wav = tts.tts(text=text, speaker_wav=reference_wav, language=language or DEFAULT_LANGUAGE)
            return wav, sample_rate

        _engine = {"name": "xtts", "synth": synth, "model": XTTS_MODEL}

    print(f"[voxstudio] engine ready: {_engine['name']} ({_engine['model']}).")
    return _engine


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

    engine = get_engine()
    try:
        wav, sample_rate = engine["synth"](req.text, ref_path, req.language)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {exc}")

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
    name = selected_engine()
    label = "VoxCPM2 (48 kHz)" if name == "voxcpm" else "Coqui XTTS-v2 (24 kHz)"
    return {
        "status": "ok",
        "voices": len(list_voices()),
        "engine": name,
        "engine_label": label,
        "model": engine_model_id(name),
        "loaded": _engine is not None,
    }


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("VOXSTUDIO_HOST", "127.0.0.1")
    port = int(os.environ.get("VOXSTUDIO_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
