import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from app.models.channel_schemas import CrawlRunSummary
from app.services.channel_crawler import CHANNELS_CSV, get_enabled_channels, load_channels, sync_channels_from_csv
from app.services.crawl_scheduler import (
    execute_daily_crawl,
    get_crawl_history,
    get_crawl_status,
    get_schedule_info,
    reprocess_missing,
)

router = APIRouter()


@router.post("/trigger")
async def trigger_crawl():
    """Manually trigger a channel crawl."""
    run_id = asyncio.ensure_future(execute_daily_crawl())
    # Give it a moment to start
    await asyncio.sleep(0.1)
    return {"message": "Crawl triggered", "status": "started"}


@router.post("/trigger/sync", response_model=CrawlRunSummary)
async def trigger_crawl_sync():
    """Trigger a crawl and wait for completion."""
    run_id = await execute_daily_crawl()
    if not run_id:
        raise HTTPException(status_code=409, detail="Crawl already in progress")
    summary = get_crawl_status(run_id)
    return summary


@router.get("/status/{run_id}", response_model=CrawlRunSummary)
async def crawl_status(run_id: str):
    summary = get_crawl_status(run_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Crawl run not found")
    return summary


@router.get("/history", response_model=list[CrawlRunSummary])
async def crawl_history():
    return get_crawl_history()


@router.get("/channels")
async def list_channels():
    channels = load_channels()
    return {
        "channels": [ch.model_dump() for ch in channels],
        "total": len(channels),
        "enabled": len([ch for ch in channels if ch.enabled]),
    }


@router.post("/sync")
async def sync_csv():
    """Sync channels.json with channels.csv."""
    result = sync_channels_from_csv()
    return result


@router.post("/upload-csv")
async def upload_csv(request: Request):
    """Upload a new channels.csv and sync."""
    body = await request.body()
    csv_text = body.decode("utf-8")

    with open(CHANNELS_CSV, "w", encoding="utf-8") as f:
        f.write(csv_text)

    result = sync_channels_from_csv()
    return result


@router.post("/reprocess")
async def trigger_reprocess():
    """Re-process existing videos that are missing subtitles or comments."""
    result = await reprocess_missing()
    return result


@router.get("/schedule")
async def schedule_info():
    return get_schedule_info()
