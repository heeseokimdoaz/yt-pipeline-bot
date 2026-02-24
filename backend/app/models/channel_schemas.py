from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ChannelConfig(BaseModel):
    channel_id: str = ""
    channel_name: str
    handle: str = ""
    uploads_playlist_id: str = ""
    category: Literal["중립/종합", "진보", "보수"] = "중립/종합"
    description: str = ""
    enabled: bool = True


class CrawlRunSummary(BaseModel):
    run_id: str
    status: str = "running"  # running | completed | error
    started_at: str = ""
    completed_at: str | None = None
    channels_processed: int = 0
    channels_total: int = 0
    new_videos_found: int = 0
    videos_skipped_duplicate: int = 0
    subtitles_collected: int = 0
    comments_collected: int = 0
    errors: list[dict] = []


class ChannelCrawlResult(BaseModel):
    channel_id: str
    channel_name: str
    category: str
    new_videos: int = 0
    skipped_videos: int = 0
    subtitles_collected: int = 0
    comments_collected: int = 0
    error: str | None = None
