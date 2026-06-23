import os
import json
import subprocess
import anthropic
import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def find_highlight(video_path: str, transcript: str, segments: list, api_key: str = None) -> dict:
    """Use Claude to find the most engaging 20-second segment."""
    key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")

    # Get video duration
    duration = _get_duration(video_path)

    if key and key.startswith("sk-ant"):
        return _find_with_claude(transcript, segments, duration, key)
    else:
        return _find_heuristic(segments, duration)


def _find_with_claude(transcript: str, segments: list, duration: float, api_key: str) -> dict:
    client = anthropic.Anthropic(api_key=api_key)

    segments_text = "\n".join(
        f"[{s['start']:.1f}s ~ {s['end']:.1f}s] {s['text']}"
        for s in segments
    ) if segments else transcript

    prompt = f"""아래는 영상의 전사 스크립트입니다 (총 길이: {duration:.1f}초).

{segments_text}

숏츠(Shorts) 용으로 가장 임팩트 있는 20초 내외의 구간을 선택해주세요.
선택 기준:
- 시청자의 이목을 단번에 끄는 흥미로운 내용
- 가능하면 완결된 문장/이야기가 포함된 구간
- 핵심 메시지나 감정이 담긴 구간

반드시 아래 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{{"start": 시작초, "end": 종료초, "reason": "선택 이유 (한국어 1~2문장)"}}"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )

    text = message.content[0].text.strip()
    # Extract JSON even if surrounded by markdown code blocks
    if "```" in text:
        text = text.split("```")[1].lstrip("json").strip()

    data = json.loads(text)
    start = float(data["start"])
    end = float(data["end"])

    # Clamp to video duration and enforce max 25 seconds
    end = min(end, duration)
    if end - start > 25:
        end = start + 20
    if end - start < 5:
        end = min(start + 20, duration)

    return {
        "start": round(start, 2),
        "end": round(end, 2),
        "reason": data.get("reason", ""),
        "method": "claude",
    }


def _find_heuristic(segments: list, duration: float) -> dict:
    """Fallback: pick the segment with the most words in a 20s window."""
    if not segments:
        start = max(0, duration * 0.1)
        return {
            "start": round(start, 2),
            "end": round(min(start + 20, duration), 2),
            "reason": "전사 내용이 없어 영상 초반부를 선택했습니다.",
            "method": "heuristic",
        }

    window = 20.0
    best_start = segments[0]["start"]
    best_count = 0

    for i, seg in enumerate(segments):
        win_end = seg["start"] + window
        word_count = sum(
            len(s["text"].split())
            for s in segments
            if seg["start"] <= s["start"] < win_end
        )
        if word_count > best_count:
            best_count = word_count
            best_start = seg["start"]

    return {
        "start": round(best_start, 2),
        "end": round(min(best_start + 20, duration), 2),
        "reason": "API 키 없이 단어 밀도 기반으로 구간을 선택했습니다.",
        "method": "heuristic",
    }


def _get_duration(video_path: str) -> float:
    result = subprocess.run(
        [FFMPEG, "-i", video_path],
        capture_output=True, text=True,
    )
    import re
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.?\d*)", result.stderr)
    if m:
        h, mn, s = m.groups()
        return int(h) * 3600 + int(mn) * 60 + float(s)
    return 60.0
