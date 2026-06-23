import subprocess
import os
import json
import tempfile
import anthropic
import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def render_shorts(
    clip_path: str,
    video_id: str,
    title: str,
    subtitles: list,
    output_dir: str,
    transcript: str = "",
    segments: list = None,
    start_offset: float = 0.0,
    api_key: str = None,
) -> dict:
    """Add title overlay and subtitles, then export the final Shorts video."""
    key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    segments = segments or []

    # Generate title if not provided
    if not title and transcript:
        title = _generate_title(transcript, key)
    if not title:
        title = "지금 바로 봐야 할 영상"

    # Generate subtitles from segments if not provided
    if not subtitles and segments:
        subtitles = _build_subtitles(segments, start_offset)

    out_path = os.path.join(output_dir, f"{video_id}_final.mp4")

    if subtitles:
        srt_path = _write_srt(subtitles, video_id, output_dir)
        _render_with_subs(clip_path, srt_path, title, out_path)
        os.remove(srt_path)
    else:
        _render_title_only(clip_path, title, out_path)

    return {
        "output_path": out_path,
        "title": title,
        "subtitle_count": len(subtitles),
    }


def _generate_title(transcript: str, api_key: str) -> str:
    if not api_key or not api_key.startswith("sk-ant"):
        return _fallback_title(transcript)

    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=120,
        messages=[{
            "role": "user",
            "content": f"""아래 영상 내용을 바탕으로 숏츠(Shorts) 제목을 만들어주세요.

조건:
- 15자 이내
- 시청자가 클릭하고 싶을 만큼 강렬하고 흥미로워야 함
- 이모지 1개 포함 가능
- 제목만 출력 (따옴표 없이)

영상 내용:
{transcript[:600]}"""
        }],
    )
    return msg.content[0].text.strip().strip('"').strip("'")


def _fallback_title(transcript: str) -> str:
    words = transcript.split()[:6]
    return " ".join(words) + "..." if words else "지금 봐야 할 영상"


def _build_subtitles(segments: list, start_offset: float) -> list:
    subs = []
    for seg in segments:
        s = seg["start"] - start_offset
        e = seg["end"] - start_offset
        if e < 0 or s > 25:
            continue
        s = max(0, s)
        subs.append({"start": round(s, 2), "end": round(max(e, s + 0.5), 2), "text": seg["text"]})
    return subs


def _write_srt(subtitles: list, video_id: str, output_dir: str) -> str:
    path = os.path.join(output_dir, f"{video_id}.srt")
    with open(path, "w", encoding="utf-8") as f:
        for i, sub in enumerate(subtitles, 1):
            f.write(f"{i}\n")
            f.write(f"{_srt_time(sub['start'])} --> {_srt_time(sub['end'])}\n")
            f.write(f"{sub['text']}\n\n")
    return path


def _srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _render_with_subs(clip_path: str, srt_path: str, title: str, out_path: str):
    # Escape special chars for FFmpeg drawtext
    safe_title = title.replace("'", "\\'").replace(":", "\\:").replace("\\", "\\\\")
    srt_escaped = srt_path.replace("'", "\\'").replace("\\", "/")

    vf = (
        f"subtitles='{srt_escaped}':force_style='FontSize=22,PrimaryColour=&HFFFFFF,"
        f"OutlineColour=&H80000000,Outline=2,Alignment=2,MarginV=80',"
        f"drawtext=text='{safe_title}':fontsize=36:fontcolor=white:"
        f"x=(w-text_w)/2:y=80:box=1:boxcolor=black@0.55:boxborderw=12:"
        f"font='NanumGothic\\|Arial Bold'"
    )

    cmd = [
        FFMPEG, "-y",
        "-i", clip_path,
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-c:a", "copy",
        "-movflags", "+faststart",
        out_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # Fallback: render without subtitle filter if libass missing
        _render_title_only(clip_path, title, out_path)


def _render_title_only(clip_path: str, title: str, out_path: str):
    safe_title = title.replace("'", "\\'").replace(":", "\\:").replace("\\", "\\\\")
    vf = (
        f"drawtext=text='{safe_title}':fontsize=38:fontcolor=white:"
        f"x=(w-text_w)/2:y=80:box=1:boxcolor=black@0.6:boxborderw=14:"
        f"font='Arial Bold'"
    )
    cmd = [
        FFMPEG, "-y",
        "-i", clip_path,
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-c:a", "copy",
        "-movflags", "+faststart",
        out_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"렌더링 실패: {result.stderr[-400:]}")
