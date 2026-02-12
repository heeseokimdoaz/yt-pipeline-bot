import re


def chunk_subtitle_segments(
    segments: list[dict], max_chars: int = 500
) -> list[dict]:
    """Merge consecutive subtitle segments into chunks of ~max_chars."""
    if not segments:
        return []

    chunks = []
    current_text = ""
    current_start = segments[0]["start"]
    current_end = 0.0

    for seg in segments:
        if len(current_text) + len(seg["text"]) > max_chars and current_text:
            chunks.append(
                {
                    "text": current_text.strip(),
                    "start_time": current_start,
                    "end_time": current_end,
                }
            )
            current_text = seg["text"]
            current_start = seg["start"]
        else:
            current_text += " " + seg["text"]
        current_end = seg["start"] + seg["duration"]

    if current_text.strip():
        chunks.append(
            {
                "text": current_text.strip(),
                "start_time": current_start,
                "end_time": current_end,
            }
        )

    return chunks


def normalize_korean_text(text: str) -> str:
    """Basic Korean text normalization for better embedding quality."""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[ㅋㅎㅠㅜ]{3,}", "", text)
    return text.strip()
