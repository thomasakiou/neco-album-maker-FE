from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:ebimobowei81@localhost:5432/album_db"
    media_root: str = "./media"
    page_size_default: int = 50
    max_photo_upload_size_mb: int = 10
    
    @property
    def albums_dir(self) -> Path:
        return Path(self.media_root) / "albums"
    
    @property
    def photos_dir(self) -> Path:
        # return Path(self.media_root) / "photos"
        return Path("C:/photo/ssceint2025")
    
    class Config:
        env_file = ".env"


settings = Settings()