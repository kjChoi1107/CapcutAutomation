import subprocess
import json
import os
import re
from math import gcd
import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def get_video_info(video_path: str) -> dict:
    """Extract video metadata using ffmpeg -i (stderr parsing)."""
    result = subprocess.run(
        [FFMPEG, "-i", video_path],
        capture_output=True,
        text=True,
    )
    stderr = result.stderr

    info = {
        "file": os.path.basename(video_path),
        "path": video_path,
        "duration": 0.0,
        "width": 0,
        "height": 0,
        "fps": 0.0,
        "codec": "",
        "has_audio": False,
        "file_size_mb": 0.0,
        "aspect_ratio": "",
    }

    # Duration
    dur_match = re.search(r"Duration: (\d+):(\d+):(\d+\.?\d*)", stderr)
    if dur_match:
        h, m, s = dur_match.groups()
        info["duration"] = round(int(h) * 3600 + int(m) * 60 + float(s), 2)

    # Video stream: codec name
    codec_match = re.search(r"Video: (\w+)", stderr)
    if codec_match:
        info["codec"] = codec_match.group(1)

    # Resolution: find NNNxNNN pattern in the Video stream line
    video_line_match = re.search(r"Video:.*?(\d{2,4})x(\d{2,4})", stderr)
    if video_line_match:
        info["width"] = int(video_line_match.group(1))
        info["height"] = int(video_line_match.group(2))

    # FPS
    fps_match = re.search(r"(\d+(?:\.\d+)?) fps", stderr)
    if fps_match:
        info["fps"] = round(float(fps_match.group(1)), 2)

    # Audio
    if re.search(r"Audio:", stderr):
        info["has_audio"] = True

    # File size
    if os.path.exists(video_path):
        info["file_size_mb"] = round(os.path.getsize(video_path) / (1024 * 1024), 2)

    # Aspect ratio
    if info["width"] and info["height"]:
        g = gcd(info["width"], info["height"])
        info["aspect_ratio"] = f"{info['width']//g}:{info['height']//g}"

    return info
