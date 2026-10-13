from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret: str
    access_token_minutes: int = 15
    refresh_token_days: int = 60

    # Comma-separated OAuth client IDs accepted as ID token audience.
    google_client_ids: str = ""
    apple_client_ids: str = ""

    # Garment photos live here, one folder per user.
    storage_dir: str = "storage"

    openrouter_api_key: str = ""
    vision_model: str = "google/gemini-3.1-flash-lite"
    image_model: str = "bytedance-seed/seedream-5-0-flash"
    outfit_model: str = "google/gemini-3.1-flash-lite"

    def client_ids(self, provider: str) -> list[str]:
        raw = {"google": self.google_client_ids, "apple": self.apple_client_ids}[provider]
        return [item.strip() for item in raw.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
