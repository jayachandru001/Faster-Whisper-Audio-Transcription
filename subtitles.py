"""Subtitle formatters for SRT and WebVTT outputs with smart word-level chunking."""

from typing import List, Dict, Any


def format_timestamp(seconds: float, separator: str = ",") -> str:
    """Format float seconds to HH:MM:SS,mmm (SRT) or HH:MM:SS.mmm (VTT)."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = min(int(round((seconds - int(seconds)) * 1000)), 999)
    return f"{hrs:02d}:{mins:02d}:{secs:02d}{separator}{millis:03d}"


def split_segment_into_cues(
    seg: Dict[str, Any],
    max_chars: int = 42,
    max_duration: float = 4.5,
    max_words: int = 8,
    pause_threshold: float = 0.5,
) -> List[Dict[str, Any]]:
    """Split coarse Whisper segments into short, readable subtitle cues using word timestamps."""
    words = seg.get("words")
    if not words:
        txt = seg.get("text", "").strip()
        if txt:
            return [{
                "start": seg.get("start", 0.0),
                "end": seg.get("end", 0.0),
                "text": txt,
            }]
        return []

    cues: List[Dict[str, Any]] = []
    current_words: List[Dict[str, Any]] = []

    def flush_cue():
        if not current_words:
            return
        cue_text = " ".join(w["word"].strip() for w in current_words).strip()
        if cue_text:
            cues.append({
                "start": current_words[0]["start"],
                "end": current_words[-1]["end"],
                "text": cue_text,
            })
        current_words.clear()

    for w in words:
        word_text = w.get("word", "").strip()
        if not word_text:
            continue

        if not current_words:
            current_words.append(w)
            continue

        current_duration = w["end"] - current_words[0]["start"]
        current_len = sum(len(x["word"].strip()) for x in current_words) + len(current_words) + len(word_text)
        prev_word = current_words[-1]
        pause = w["start"] - prev_word["end"]
        prev_text = prev_word.get("word", "").strip()
        ended_with_punctuation = prev_text.endswith((".", "?", "!", ";", ":", ","))

        should_split = (
            current_duration >= max_duration
            or current_len >= max_chars
            or len(current_words) >= max_words
            or (ended_with_punctuation and len(current_words) >= 3)
            or (pause >= pause_threshold and len(current_words) >= 2)
        )

        if should_split:
            flush_cue()

        current_words.append(w)

    flush_cue()
    return cues


def extract_subtitle_cues(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract and split all segments into fine-grained subtitle cues."""
    cues: List[Dict[str, Any]] = []
    for seg in segments:
        cues.extend(split_segment_into_cues(seg))
    return cues


def to_srt(segments: List[Dict[str, Any]]) -> str:
    """Convert segment timestamps to SubRip Subtitle (.srt) format with short, readable cues."""
    cues = extract_subtitle_cues(segments)
    lines = []
    for idx, cue in enumerate(cues, start=1):
        start = format_timestamp(cue.get("start", 0.0), separator=",")
        end = format_timestamp(cue.get("end", 0.0), separator=",")
        text = cue.get("text", "").strip()
        lines.append(f"{idx}\n{start} --> {end}\n{text}\n")
    return "\n".join(lines).strip() + "\n"


def to_vtt(segments: List[Dict[str, Any]]) -> str:
    """Convert segment timestamps to Web Video Text Tracks (.vtt) format with short, readable cues."""
    cues = extract_subtitle_cues(segments)
    lines = ["WEBVTT\n"]
    for idx, cue in enumerate(cues, start=1):
        start = format_timestamp(cue.get("start", 0.0), separator=".")
        end = format_timestamp(cue.get("end", 0.0), separator=".")
        text = cue.get("text", "").strip()
        lines.append(f"{idx}\n{start} --> {end}\n{text}\n")
    return "\n".join(lines).strip() + "\n"
