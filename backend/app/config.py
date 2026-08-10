from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openrouter_api_key: str
    database_url: str = "sqlite:///./thesis_tracker.db"
    openrouter_model: str = "openrouter/free"
    cors_origins: str = "http://localhost:3000"


settings = Settings()  # type: ignore[call-arg]
