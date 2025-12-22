from pydantic import BaseModel
from typing import Optional


class AlbumGenerationToDiskRequest(BaseModel):
    state_code: str
    exam_title: str
    batch: Optional[str] = None  # None means "All Batches"
    save_path: str = "C:/albums"
