from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openrouter_api_key: str
    database_url: str = "sqlite:///./vault_index.db"
    openrouter_model: str = "openrouter/free"
    cors_origins: str = "http://localhost:3000"
    vault_path: Path = Path("../vault")

    @field_validator("vault_path")
    @classmethod
    def resolve_vault_path(cls, v: Path) -> Path:
        return v.resolve()


settings = Settings()  # type: ignore[call-arg]
