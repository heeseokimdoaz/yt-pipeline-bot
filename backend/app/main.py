from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import crawler, pipeline, search, videos
from app.services.channel_crawler import sync_channels_from_csv
from app.services.crawl_scheduler import shutdown_scheduler, start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    sync_channels_from_csv()
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="YouTube Pipeline Bot", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3100"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pipeline.router, prefix="/api/pipeline", tags=["pipeline"])
app.include_router(videos.router, prefix="/api/videos", tags=["videos"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(crawler.router, prefix="/api/crawler", tags=["crawler"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}
