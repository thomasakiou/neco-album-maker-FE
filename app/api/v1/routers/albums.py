import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.core.config import settings
from app.domain.models.student import Student
from app.infra.pdf.generator import PDFGenerator

router = APIRouter(prefix="/albums", tags=["albums"])


class GenerateAlbumRequest(BaseModel):
    school_id: Optional[str] = None
    state_code: Optional[str] = None
    batch: Optional[str] = None
    format: str = "pdf"
    layout: str = "grid_3x4"
    include_missing_photos: bool = False


@router.post("/generate")
async def generate_album(
    request: GenerateAlbumRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db)
):
    from sqlalchemy.orm import selectinload
    from app.domain.models.school import School
    
    # Build query with eager loading
    query = select(Student).options(selectinload(Student.school)).join(School, Student.school_id == School.id, isouter=True)
    
    if request.state_code:
        query = query.where(School.state == request.state_code)
    if request.school_id:
        query = query.where(Student.school_id == request.school_id)
    if request.batch:
        query = query.where(Student.batch == request.batch)
    
    result = await session.execute(query)
    students = result.scalars().all()
    
    if not students:
        raise HTTPException(status_code=404, detail="No students found")
    
    # Generate filename
    album_id = str(uuid.uuid4())
    if request.state_code:
        state_name = students[0].school.state_name if students[0].school else request.state_code
        filename = f"{state_name}_{album_id}.pdf"
    else:
        school_name = students[0].school.sch_name if students[0].school else "unknown"
        batch = request.batch or students[0].batch
        filename = f"{school_name}_{batch}_{album_id}.pdf"
    
    # Ensure albums directory exists
    settings.albums_dir.mkdir(parents=True, exist_ok=True)
    output_path = settings.albums_dir / filename
    
    # Generate PDF
    generator = PDFGenerator()
    generator.generate_album(students, str(output_path), request.layout)
    
    return {
        "album_id": album_id,
        "filename": filename,
        "students_count": len(students),
        "download_url": f"/api/v1/albums/{album_id}/download"
    }


@router.get("/{album_id}/download")
async def download_album(album_id: str):
    # Find album file
    albums_dir = settings.albums_dir
    album_files = list(albums_dir.glob(f"*_{album_id}.pdf"))
    
    if not album_files:
        raise HTTPException(status_code=404, detail="Album not found")
    
    album_file = album_files[0]
    return FileResponse(
        path=album_file,
        filename=album_file.name,
        media_type="application/pdf"
    )


@router.delete("/{album_id}")
async def delete_album(album_id: str):
    albums_dir = settings.albums_dir
    album_files = list(albums_dir.glob(f"*_{album_id}.pdf"))
    
    if not album_files:
        raise HTTPException(status_code=404, detail="Album not found")
    
    album_file = album_files[0]
    album_file.unlink()
    
    return {"message": "Album deleted"}