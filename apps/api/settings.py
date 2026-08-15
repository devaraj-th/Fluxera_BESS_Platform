from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./fluxera.local.db"
    environment: str = "local"
    max_upload_bytes: int = 50 * 1024 * 1024
    max_pdf_pages: int = 500
    storage_dir: str = "./private-storage"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    model_config = SettingsConfigDict(env_prefix="FLUXERA_", env_file=".env", extra="ignore")

    @property
    def allowed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
