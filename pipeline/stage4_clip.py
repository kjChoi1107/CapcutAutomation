import subprocess
import os
import re
import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

TARGET_W = 1080
TARGET_H = 1920


def create_clip(video_path: str, video_id: str, start: float, end: float, output_dir: str) -> dict:
    """Extract clip and convert to 9:16 vertical (1080x1920)."""
    duration = end - start
    out_path = os.path.join(output_dir, f"{video_id}_clip.mp4")

    # Get source dimensions
    src_w, src_h = _get_dimensions(video_path)

    # Build FFmpeg filter for vertical crop/pad
    vf = _build_vertical_filter(src_w, src_h)

    cmd = [
        FFMPEG, "-y",
        "-ss", str(start),
        "-i", video_path,
        "-t", str(duration),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        out_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg 오류: {result.stderr[-500:]}")

    return {
        "clip_path": out_path,
        "duration": round(duration, 2),
        "resolution": f"{TARGET_W}x{TARGET_H}",
        "start": start,
        "end": end,
    }


def _build_vertical_filter(src_w: int, src_h: int) -> str:
    """Build FFmpeg -vf string to produce 1080x1920 vertical video."""
    src_ratio = src_w / src_h if src_h else 1
    target_ratio = TARGET_W / TARGET_H  # 0.5625 (9:16)

    if src_ratio > target_ratio:
        # Wider than 9:16: scale by height, then crop width
        scale = f"scale=-2:{TARGET_H}"
        crop = f"crop={TARGET_W}:{TARGET_H}"
        return f"{scale},{crop}"
    elif src_ratio < target_ratio:
        # Taller than 9:16: scale by width, then crop height
        scale = f"scale={TARGET_W}:-2"
        crop = f"crop={TARGET_W}:{TARGET_H}"
        return f"{scale},{crop}"
    else:
        # Already 9:16
        return f"scale={TARGET_W}:{TARGET_H}"


def _get_dimensions(video_path: str) -> tuple:
    result = subprocess.run(
        [FFMPEG, "-i", video_path],
        capture_output=True, text=True,
    )
    m = re.search(r"(\d{3,4})x(\d{3,4})", result.stderr)
    if m:
        return int(m.group(1)), int(m.group(2))
    return 1920, 1080
