from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    project_name: str = "my-service"
    version: str = "2.0.0"
    env: str = "production"
    port: int = 8000
    debug: bool = False

    # Security – override via environment variables in production
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/myservice"
    db_pool_max: int = 20
    db_pool_min: int = 2

    # Redis
    redis_url: str = "redis://redis:6379/0"
    cache_ttl: int = 300

    # Rate limiting (requests per window)
    rate_limit_requests: int = 100
    rate_limit_window: str = "1 minute"

    # CORS
    cors_origins: list[str] = ["*"]

    # Deployment
    replicas: int = 2
    timeout: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
