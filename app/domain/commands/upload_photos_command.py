from dataclasses import dataclass
from typing import Optional


@dataclass
class UploadPhotosCommand:
    zip_path: Optional[str] = None
    individual_files: Optional[list[tuple[str, bytes]]] = None


@dataclass
class UploadPhotosResult:
    saved: int
    missing_students: list[str]
    errors: list[str]