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

    # Abuse limits: guest accounts per IP address, garments and looks per user (all paid).
    guest_accounts_per_hour: int = 20
    garments_per_day: int = 200
    inspirations_per_day: int = 30

    def client_ids(self, provider: str) -> list[str]:
        raw = {"google": self.google_client_ids, "apple": self.apple_client_ids}[provider]
        return [item.strip() for item in raw.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
