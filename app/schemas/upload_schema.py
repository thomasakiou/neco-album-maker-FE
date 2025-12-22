from pydantic import BaseModel

class ScanPhotosRequest(BaseModel):
    path: str
