import os
import uuid
import asyncio
import mimetypes
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import HTMLResponse, Response, JSONResponse
import uvicorn

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
STATIC_DIR = BASE_DIR / "static"

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Shorts Auto Editor")

# Cache index.html at startup (sync read in main thread, avoids anyio thread pool)
_INDEX_HTML: str = (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/")
async def index():
    return HTMLResponse(_INDEX_HTML)


@app.get("/output/{filename}")
async def serve_output(filename: str):
    """Serve output video files synchronously (bypasses anyio thread pool)."""
    path = OUTPUT_DIR / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(404, "파일을 찾을 수 없습니다.")
    mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    data = path.read_bytes()
    return Response(content=data, media_type=mime)


@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    """Stage 1: Upload video and extract basic metadata."""
    allowed = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed:
        raise HTTPException(400, f"지원하지 않는 형식입니다: {ext}")

    video_id = str(uuid.uuid4())[:8]
    save_path = UPLOAD_DIR / f"{video_id}{ext}"

    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    from pipeline.stage1_analyze import get_video_info
    info = get_video_info(str(save_path))
    info["video_id"] = video_id
    info["stage"] = 1

    return JSONResponse(info)


@app.post("/api/transcribe/{video_id}")
async def transcribe_video(video_id: str, data: dict = None):
    """Stage 2: Transcribe audio using Whisper."""
    video_path = _find_video(video_id)
    model_name = (data or {}).get("model", "small")

    from pipeline.stage2_transcribe import transcribe
    result = await asyncio.to_thread(transcribe, str(video_path), model_name)
    result["video_id"] = video_id
    result["stage"] = 2
    result["model"] = model_name
    return JSONResponse(result)


@app.post("/api/highlight/{video_id}")
async def detect_highlight(video_id: str, request: Request, data: dict = None):
    """Stage 3: Use Claude to find the best 20-second highlight."""
    video_path = _find_video(video_id)
    body = data or {}
    transcript = body.get("transcript", "")
    segments = body.get("segments", [])
    api_key = body.get("api_key") or request.headers.get("X-Api-Key", "")

    from pipeline.stage3_highlight import find_highlight
    result = await asyncio.to_thread(find_highlight, str(video_path), transcript, segments, api_key)
    result["video_id"] = video_id
    result["stage"] = 3
    return JSONResponse(result)


@app.post("/api/clip/{video_id}")
async def clip_video(video_id: str, data: dict = None):
    """Stage 4: Extract clip and convert to 9:16 vertical format."""
    video_path = _find_video(video_id)
    start = (data or {}).get("start", 0)
    end = (data or {}).get("end", 20)

    from pipeline.stage4_clip import create_clip
    result = await asyncio.to_thread(create_clip, str(video_path), video_id, start, end, str(OUTPUT_DIR))
    result["video_id"] = video_id
    result["stage"] = 4
    return JSONResponse(result)


@app.post("/api/render/{video_id}")
async def render_final(video_id: str, request: Request, data: dict = None):
    """Stage 5: Add title overlay and subtitles, export final video."""
    data = data or {}
    title = data.get("title", "")
    subtitles = data.get("subtitles", [])
    transcript = data.get("transcript", "")
    segments = data.get("segments", [])
    start_offset = data.get("start", 0.0)
    api_key = data.get("api_key") or request.headers.get("X-Api-Key", "")
    clip_path = str(OUTPUT_DIR / f"{video_id}_clip.mp4")

    if not os.path.exists(clip_path):
        raise HTTPException(404, "클립이 없습니다. Stage 4를 먼저 실행하세요.")

    from pipeline.stage5_render import render_shorts
    result = await asyncio.to_thread(
        render_shorts, clip_path, video_id, title, subtitles,
        str(OUTPUT_DIR), transcript, segments, start_offset, api_key,
    )
    result["video_id"] = video_id
    result["stage"] = 5
    return JSONResponse(result)


@app.get("/api/status")
async def status():
    return {"status": "running", "version": "1.0.0"}


def _find_video(video_id: str) -> Path:
    for ext in [".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"]:
        p = UPLOAD_DIR / f"{video_id}{ext}"
        if p.exists():
            return p
    raise HTTPException(404, f"영상을 찾을 수 없습니다: {video_id}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
