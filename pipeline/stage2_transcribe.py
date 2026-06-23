import whisper
import os
import imageio_ffmpeg

# Whisper calls "ffmpeg" by name; create a named symlink in /tmp and prepend to PATH
_ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
_ffmpeg_link = "/tmp/ffmpeg"
if not os.path.exists(_ffmpeg_link):
    os.symlink(_ffmpeg_exe, _ffmpeg_link)
if "/tmp" not in os.environ.get("PATH", "").split(os.pathsep):
    os.environ["PATH"] = "/tmp" + os.pathsep + os.environ.get("PATH", "")

_model_cache: dict = {}


def _get_model(name: str):
    if name not in _model_cache:
        _model_cache[name] = whisper.load_model(name)
    return _model_cache[name]


def transcribe(video_path: str, model_name: str = "small") -> dict:
    """Transcribe video audio using Whisper. Returns text + timestamped segments."""
    model = _get_model(model_name)

    result = model.transcribe(video_path, word_timestamps=False, verbose=False)

    segments = [
        {
            "start": round(s["start"], 2),
            "end": round(s["end"], 2),
            "text": s["text"].strip(),
        }
        for s in result.get("segments", [])
    ]

    return {
        "text": result.get("text", "").strip(),
        "language": result.get("language", "unknown"),
        "segments": segments,
    }
