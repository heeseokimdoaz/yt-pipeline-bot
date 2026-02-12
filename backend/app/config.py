from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    youtube_api_key: str = ""
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    backend_port: int = 8001
    log_level: str = "info"
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    youtube_daily_quota_limit: int = 10000

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
