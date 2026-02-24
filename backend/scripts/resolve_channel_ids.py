"""
Resolve YouTube channel handles to channel IDs.

Usage:
    cd backend && python -m scripts.resolve_channel_ids

Reads channels from 'app/data/channels.json' (handle field),
resolves each handle to a channel_id via YouTube Data API,
and writes the updated file back.

Requires YOUTUBE_API_KEY environment variable.
Cost: 1 quota unit per channel (channels.list), ~30 units total.
"""

import json
import os
import sys
from pathlib import Path

from googleapiclient.discovery import build

CHANNELS_PATH = Path(__file__).resolve().parent.parent / "app" / "data" / "channels.json"


def main():
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print("ERROR: Set YOUTUBE_API_KEY environment variable first.")
        sys.exit(1)

    youtube = build("youtube", "v3", developerKey=api_key)

    with open(CHANNELS_PATH, encoding="utf-8") as f:
        channels = json.load(f)

    print(f"Loaded {len(channels)} channels.\n")

    resolved = 0
    skipped = 0

    for ch in channels:
        name = ch["channel_name"]

        if ch.get("channel_id"):
            print(f"[SKIP] {name} — already resolved: {ch['channel_id']}")
            skipped += 1
            continue

        handle = ch.get("handle", "")
        if not handle:
            print(f"[WARN] {name} — no handle, skipping.")
            continue

        # Remove @ prefix if present for the API call
        handle_clean = handle.lstrip("@")

        try:
            response = (
                youtube.channels()
                .list(part="id,snippet", forHandle=handle_clean)
                .execute()
            )
        except Exception as e:
            print(f"[ERROR] {name} ({handle}): {e}")
            continue

        items = response.get("items", [])
        if not items:
            print(f"[MISS] {name} ({handle}) — no channel found for handle.")
            continue

        channel_id = items[0]["id"]
        uploads_id = "UU" + channel_id[2:] if channel_id.startswith("UC") else ""

        ch["channel_id"] = channel_id
        ch["uploads_playlist_id"] = uploads_id

        actual_title = items[0]["snippet"]["title"]
        print(f"[OK] {name} ({handle}) → {channel_id} (title: {actual_title})")
        resolved += 1

    with open(CHANNELS_PATH, "w", encoding="utf-8") as f:
        json.dump(channels, f, ensure_ascii=False, indent=2)

    print(f"\nDone! Resolved: {resolved}, Skipped: {skipped}, Total: {len(channels)}")
    print(f"Saved to: {CHANNELS_PATH}")


if __name__ == "__main__":
    main()
