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

    # Subtitle extraction resilience
    subtitle_socket_timeout: int = 120  # seconds; increased for long videos
    subtitle_max_retries: int = 3
    subtitle_retry_base_delay: float = 3.0  # seconds; exponential backoff base
    subtitle_throttle_min: float = 2.0  # min seconds between extractions
    subtitle_throttle_max: float = 5.0  # max seconds between extractions

    # Proxy rotation for yt-dlp (comma-separated list of proxy URLs)
    # e.g. "socks5://proxy1:1080,http://proxy2:8080,socks5://proxy3:1080"
    subtitle_proxies: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
