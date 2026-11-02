"""Subtitle formatters for SRT and WebVTT outputs."""

from typing import List, Dict, Any


def format_timestamp(seconds: float, separator: str = ",") -> str:
    """Format float seconds to HH:MM:SS,mmm (SRT) or HH:MM:SS.mmm (VTT)."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = min(int(round((seconds - int(seconds)) * 1000)), 999)
    return f"{hrs:02d}:{mins:02d}:{secs:02d}{separator}{millis:03d}"


def to_srt(segments: List[Dict[str, Any]]) -> str:
    """Convert segment timestamps to SubRip Subtitle (.srt) format."""
    lines = []
    for idx, seg in enumerate(segments, start=1):
        start = format_timestamp(seg.get("start", 0.0), separator=",")
        end = format_timestamp(seg.get("end", 0.0), separator=",")
        text = seg.get("text", "").strip()
        lines.append(f"{idx}\n{start} --> {end}\n{text}\n")
    return "\n".join(lines).strip() + "\n"


def to_vtt(segments: List[Dict[str, Any]]) -> str:
    """Convert segment timestamps to Web Video Text Tracks (.vtt) format."""
    lines = ["WEBVTT\n"]
    for idx, seg in enumerate(segments, start=1):
        start = format_timestamp(seg.get("start", 0.0), separator=".")
        end = format_timestamp(seg.get("end", 0.0), separator=".")
        text = seg.get("text", "").strip()
        lines.append(f"{idx}\n{start} --> {end}\n{text}\n")
    return "\n".join(lines).strip() + "\n"
