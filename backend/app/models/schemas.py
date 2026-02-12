from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# === Request Models ===


class PipelineRequest(BaseModel):
    keywords: list[str]
    max_results: int = Field(default=10, le=50)
    filter_keywords: list[str] = []
    filter_mode: Literal["any", "all"] = "any"
    include_subtitles: bool = True
    include_comments: bool = True
    subtitle_languages: list[str] = ["ko", "en"]
    max_comments_per_video: int = 100


class SearchRequest(BaseModel):
    query: str
    n_results: int = Field(default=10, le=50)
    collection: Literal["videos", "subtitles", "comments"] = "subtitles"


# === Data Models ===


class VideoData(BaseModel):
    video_id: str
    title: str
    channel_title: str
    published_at: str
    view_count: int | None = None
    like_count: int | None = None
    comment_count_api: int | None = None
    description: str = ""
    tags: list[str] = []
    thumbnail_url: str = ""


class SubtitleSegment(BaseModel):
    text: str
    start: float
    duration: float


class SubtitleResult(BaseModel):
    video_id: str
    language: str
    is_generated: bool
    segments: list[SubtitleSegment]


class CommentData(BaseModel):
    comment_id: str
    author: str
    text: str
    like_count: int
    published_at: str
    is_reply: bool


# === Response Models ===


class PipelineResponse(BaseModel):
    run_id: str
    status: str
    sse_url: str


class VideoSummary(BaseModel):
    video_id: str
    title: str
    channel_title: str
    published_at: str
    view_count: int | None = None
    description: str = ""
    thumbnail_url: str = ""
    has_subtitles: bool = False
    comment_count: int = 0


class VideoDetail(BaseModel):
    video: VideoSummary
    subtitles: list[SubtitleSegment] = []
    subtitle_language: str | None = None
    comments: list[CommentData] = []


class PipelineRunSummary(BaseModel):
    run_id: str
    keywords: list[str]
    status: str
    started_at: str
    video_count: int = 0
    subtitle_count: int = 0
    comment_count: int = 0


class SearchResult(BaseModel):
    id: str
    document: str
    metadata: dict
    distance: float | None = None
