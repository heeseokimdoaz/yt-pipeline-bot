from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import pipeline, videos, search

app = FastAPI(title="YouTube Pipeline Bot", version="1.0.0")

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


@app.get("/health")
async def health_check():
    return {"status": "ok"}
