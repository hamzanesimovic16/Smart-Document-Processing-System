from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Gemini API
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # Database — SQLite file, lives next to the app
    database_url: str = "sqlite:///./sdp.db"

    # File storage
    upload_dir: Path = Path("./uploads")

    # CORS — comma-separated list of allowed origins for the frontend
    cors_origins: str = "http://localhost:4200,http://localhost:3000"

    # OCR — set to None on systems where tesseract is on PATH
    tesseract_cmd: str | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
settings.upload_dir.mkdir(parents=True, exist_ok=True)
