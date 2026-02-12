from __future__ import annotations

import logging
from typing import Optional

import chromadb
from chromadb.utils import embedding_functions

from app.config import settings
from app.models.schemas import (
    CommentData,
    SearchResult,
    SubtitleResult,
    VideoData,
)
from app.utils.text_processing import chunk_subtitle_segments, normalize_korean_text

logger = logging.getLogger(__name__)

_client: chromadb.HttpClient | None = None
_embedding_fn = None


def get_client() -> chromadb.HttpClient:
    global _client
    if _client is None:
        _client = chromadb.HttpClient(
            host=settings.chroma_host, port=settings.chroma_port
        )
    return _client


def get_embedding_function():
    global _embedding_fn
    if _embedding_fn is None:
        _embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=settings.embedding_model
        )
    return _embedding_fn


def get_collection(name: str):
    return get_client().get_or_create_collection(
        name=name,
        embedding_function=get_embedding_function(),
        metadata={"hnsw:space": "cosine"},
    )


def store_videos(videos: list[VideoData], run_id: str) -> int:
    """Store video metadata in the 'videos' collection."""
    collection = get_collection("videos")
    ids = []
    documents = []
    metadatas = []

    for v in videos:
        text = normalize_korean_text(f"{v.title} {v.description}")
        ids.append(v.video_id)
        documents.append(text)
        metadatas.append(
            {
                "video_id": v.video_id,
                "run_id": run_id,
                "title": v.title,
                "channel_title": v.channel_title,
                "published_at": v.published_at,
                "view_count": v.view_count or 0,
                "like_count": v.like_count or 0,
                "thumbnail_url": v.thumbnail_url,
                "tags": ", ".join(v.tags[:20]),
            }
        )

    if ids:
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    return len(ids)


def store_subtitles(subtitles: SubtitleResult, run_id: str) -> int:
    """Store subtitle chunks in the 'subtitles' collection."""
    collection = get_collection("subtitles")
    segments_dicts = [
        {"text": s.text, "start": s.start, "duration": s.duration}
        for s in subtitles.segments
    ]
    chunks = chunk_subtitle_segments(segments_dicts)

    ids = []
    documents = []
    metadatas = []

    for i, chunk in enumerate(chunks):
        text = normalize_korean_text(chunk["text"])
        ids.append(f"{subtitles.video_id}_chunk_{i}")
        documents.append(text)
        metadatas.append(
            {
                "video_id": subtitles.video_id,
                "run_id": run_id,
                "language": subtitles.language,
                "start_time": chunk["start_time"],
                "end_time": chunk["end_time"],
                "chunk_index": i,
            }
        )

    if ids:
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    return len(ids)


def store_comments(
    comments: list[CommentData], video_id: str, run_id: str
) -> int:
    """Store comments in the 'comments' collection."""
    collection = get_collection("comments")
    ids = []
    documents = []
    metadatas = []

    for c in comments:
        text = normalize_korean_text(c.text)
        if not text:
            continue
        ids.append(c.comment_id)
        documents.append(text)
        metadatas.append(
            {
                "video_id": video_id,
                "run_id": run_id,
                "comment_id": c.comment_id,
                "author": c.author,
                "like_count": c.like_count,
                "published_at": c.published_at,
                "is_reply": c.is_reply,
            }
        )

    if ids:
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    return len(ids)


def search_similar(
    query: str, collection_name: str, n_results: int = 10
) -> list[SearchResult]:
    """Vector similarity search across a collection."""
    collection = get_collection(collection_name)
    results = collection.query(
        query_texts=[normalize_korean_text(query)],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    search_results = []
    if results and results["ids"] and results["ids"][0]:
        for i, doc_id in enumerate(results["ids"][0]):
            search_results.append(
                SearchResult(
                    id=doc_id,
                    document=results["documents"][0][i] if results["documents"] else "",
                    metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                    distance=results["distances"][0][i] if results["distances"] else None,
                )
            )

    return search_results


def get_video_data(run_id: str | None = None) -> list[dict]:
    """Get all videos, optionally filtered by run_id."""
    collection = get_collection("videos")
    where = {"run_id": run_id} if run_id else None
    results = collection.get(where=where, include=["documents", "metadatas"])

    items = []
    if results and results["ids"]:
        for i, doc_id in enumerate(results["ids"]):
            meta = results["metadatas"][i] if results["metadatas"] else {}
            items.append({"id": doc_id, "metadata": meta})

    return items


def get_subtitles_for_video(video_id: str) -> list[dict]:
    """Get subtitle chunks for a specific video."""
    collection = get_collection("subtitles")
    results = collection.get(
        where={"video_id": video_id},
        include=["documents", "metadatas"],
    )

    items = []
    if results and results["ids"]:
        for i, doc_id in enumerate(results["ids"]):
            items.append(
                {
                    "id": doc_id,
                    "text": results["documents"][i] if results["documents"] else "",
                    "metadata": results["metadatas"][i] if results["metadatas"] else {},
                }
            )
    items.sort(key=lambda x: x.get("metadata", {}).get("chunk_index", 0))
    return items


def get_comments_for_video(video_id: str) -> list[dict]:
    """Get comments for a specific video."""
    collection = get_collection("comments")
    results = collection.get(
        where={"video_id": video_id},
        include=["documents", "metadatas"],
    )

    items = []
    if results and results["ids"]:
        for i, doc_id in enumerate(results["ids"]):
            items.append(
                {
                    "id": doc_id,
                    "text": results["documents"][i] if results["documents"] else "",
                    "metadata": results["metadatas"][i] if results["metadatas"] else {},
                }
            )
    return items
