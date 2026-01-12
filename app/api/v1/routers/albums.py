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
from app.infra.pdf.disk_generator import DiskPDFGenerator
from app.schemas.album_schema import AlbumGenerationToDiskRequest

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


@router.post("/generate-to-disk")
async def generate_albums_to_disk(
    request: AlbumGenerationToDiskRequest,
    session: AsyncSession = Depends(get_db)
):
    from sqlalchemy.orm import selectinload
    from app.domain.models.school import School
    from app.domain.models.state import State
    from fastapi.responses import StreamingResponse
    import json
    import asyncio

    async def generate_stream():
        print(f"Starting generate-to-disk for state: {request.state_code}, batch: {request.batch or 'ALL'}")
        
        # 1. Fetch State Name
        state_query = select(State).where(State.code == request.state_code)
        state_result = await session.execute(state_query)
        state = state_result.scalar_one_or_none()
        state_name = state.state if state else request.state_code
        
        # 2. Get all school numbers for this state
        schools_query = select(School.schnum).where(School.state == request.state_code)
        schools_result = await session.execute(schools_query)
        state_schnums = [row[0] for row in schools_result.fetchall()]
        
        # 3. Fetch students
        query = (
            select(Student)
            .options(selectinload(Student.school))
            .where(Student.schnum.in_(state_schnums))
            .order_by(Student.schnum, Student.ser_no)
        )
        if request.batch:
            query = query.where(Student.batch == request.batch)
        
        result = await session.execute(query)
        students = result.scalars().all()
        
        if not students:
            yield f"data: {json.dumps({'type': 'error', 'detail': 'No students found'})}\n\n"
            return
        
        # 4. Group by school
        schools_data = {}
        for student in students:
            if student.schnum not in schools_data:
                schools_data[student.schnum] = {
                    "school": student.school,
                    "students": []
                }
            schools_data[student.schnum]["students"].append(student)
        
        # 5. Create Directory
        try:
            base_path = Path(request.save_path)
            state_dir = base_path / state_name
            state_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'detail': f'Directory error: {str(e)}'})}\n\n"
            return
        
        total_schools = len(schools_data)
        yield f"data: {json.dumps({'type': 'start', 'total': total_schools, 'output_directory': str(state_dir)})}\n\n"
        
        # 6. Generate PDFs
        generator = DiskPDFGenerator()
        files_generated = 0
        files_failed = []
        
        zip_archive = None
        if request.photos_dir and request.photos_dir.lower().endswith('.zip'):
            try:
                zip_path = Path(request.photos_dir)
                if zip_path.exists():
                    zip_archive = zipfile.ZipFile(zip_path, 'r')
            except Exception as e:
                print(f"Error opening ZIP: {e}")

        try:
            for idx, (schnum, data) in enumerate(schools_data.items()):
                school = data["school"]
                school_students = data["students"]
                
                # Yield progress BEFORE processing
                yield f"data: {json.dumps({
                    'type': 'progress',
                    'current': idx + 1,
                    'total': total_schools,
                    'schnum': schnum,
                    'count': len(school_students)
                })}\n\n"
                
                # Allow the event to be emitted immediately
                await asyncio.sleep(0.01)

                output_file = state_dir / f"{schnum}.pdf"
                try:
                    generator.generate_school_album(
                        school=school,
                        students=school_students,
                        exam_title=request.exam_title,
                        output_path=str(output_file),
                        photos_dir=request.photos_dir,
                        zip_archive=zip_archive
                    )
                    files_generated += 1
                except Exception as e:
                    files_failed.append({"schnum": schnum, "error": str(e)})

            yield f"data: {json.dumps({
                'type': 'finish',
                'status': 'success' if not files_failed else 'partial',
                'files_generated': files_generated,
                'files_failed': len(files_failed),
                'output_directory': str(state_dir).replace('\\', '/')
            })}\n\n"
        finally:
            if zip_archive:
                zip_archive.close()

    return StreamingResponse(generate_stream(), media_type="text/event-stream")