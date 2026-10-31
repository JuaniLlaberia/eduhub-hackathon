"""
Backend configuration, read from environment variables (and .env when present).
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Backend settings. Field names map to the upper-case variables in .env.example.
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    eduhub_fake_ai: bool = True
    demo_mode: bool = False
    frontend_origin: str = "http://localhost:3000"
    database_path: Path = Path("data/eduhub.sqlite3")
    fixtures_dir: Path = Path("src/backend/fixtures")
    twitterapi_io_key: str | None = None

    @property
    def frontend_origins(self) -> list[str]:
        """
        Return the allowed CORS origins from the comma-separated frontend_origin.
        """
        return [origin.strip() for origin in self.frontend_origin.split(",") if origin.strip()]
