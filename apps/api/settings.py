from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./fluxera.local.db"
    environment: str = "local"
    max_upload_bytes: int = 50 * 1024 * 1024
    max_pdf_pages: int = 500
    storage_dir: str = "./private-storage"

    model_config = SettingsConfigDict(env_prefix="FLUXERA_", env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
