from dataclasses import dataclass


@dataclass
class UploadPhotosCommand:
    zip_path: str


@dataclass
class UploadPhotosResult:
    saved: int
    missing_students: list[str]
    errors: list[str]