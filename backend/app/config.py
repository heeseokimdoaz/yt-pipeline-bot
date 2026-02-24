from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    youtube_api_key: str = ""
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    backend_port: int = 8001
    log_level: str = "info"
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    youtube_daily_quota_limit: int = 10000

    # Crawler settings
    crawl_enabled: bool = True
    crawl_hour_utc: int = 18  # 03:00 KST = 18:00 UTC
    crawl_minute: int = 0
    crawl_days_back: int = 7
    crawl_max_comments_per_video: int = 50
    crawl_subtitle_languages: list[str] = ["ko", "en"]
    crawl_min_quota_reserve: int = 2000

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
