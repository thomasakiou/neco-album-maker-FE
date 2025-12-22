from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.schemas.student_schema import StudentRead, StudentCreate, StudentUpdate, PaginatedResponse
from app.domain.repositories.interfaces import IStudentRepository, StudentFilter
from app.api.v1.deps import get_student_repo
from app.core.db import get_db
from pydantic import BaseModel
from pathlib import Path
from app.core.config import settings
import os

router = APIRouter(prefix="/students", tags=["students"])


class StudentWithSchoolDetails(BaseModel):
    reg_no: str
    cand_name: str
    ser_no: Optional[str]
    sch_name: Optional[str]
    schnum: str
    town: Optional[str]
    custodian: Optional[str]
    photo_url: Optional[str]
    batch: Optional[str] = None
    
    class Config:
        from_attributes = True


@router.get("/", response_model=PaginatedResponse)
async def list_students(
    schnum: Optional[str] = None,
    sch_name: Optional[str] = None,
    batch: Optional[str] = None,
    state_name: Optional[str] = None,
    cand_name: Optional[str] = None,
    reg_no: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    repo: IStudentRepository = Depends(get_student_repo)
):
    filters = StudentFilter(schnum, sch_name, batch, state_name, cand_name, reg_no)
    total, students = await repo.find(filters, limit, (page - 1) * limit)
    
    items = []
    for student in students:
        item = StudentRead.model_validate(student)
        if student.school:
            item.school_name = student.school.sch_name
            item.state_name = student.school.state_name
            
        # Resolve photo URL
        if student.photo_path and os.path.exists(student.photo_path):
            # Convert filesystem path to web path
            # Expected: ./media/photos/REG123.jpg -> /media/photos/REG123.jpg
            path_obj = Path(student.photo_path)
            try:
                relative = path_obj.relative_to(settings.media_root)
                item.photo_url = f"/media/{relative.as_posix()}"
            except ValueError:
                item.photo_url = "/media/null_passport.jpg"
        else:
            item.photo_url = "/media/null_passport.jpg"
            
        items.append(item)
    
    return PaginatedResponse(total=total, page=page, limit=limit, items=items)


@router.get("/batches", response_model=List[str])
async def get_available_batches(
    state_code: Optional[str] = None,
    session: AsyncSession = Depends(get_db)
):
    """Get unique batch values, optionally filtered by state code."""
    from app.domain.models.student import Student
    from app.domain.models.school import School
    from sqlalchemy import distinct
    
    if state_code:
        # Get batches for a specific state
        query = (
            select(distinct(Student.batch))
            .join(School, Student.school_id == School.id, isouter=True)
            .where(School.state == state_code)
            .where(Student.batch.isnot(None))
            .order_by(Student.batch)
        )
    else:
        # Get all unique batches
        query = (
            select(distinct(Student.batch))
            .where(Student.batch.isnot(None))
            .order_by(Student.batch)
        )
    
    result = await session.execute(query)
    batches = [row[0] for row in result.fetchall()]
    
    return batches


@router.get("/{student_id}", response_model=StudentRead)
async def get_student(
    student_id: UUID,
    repo: IStudentRepository = Depends(get_student_repo)
):
    student = await repo.get_by_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    result = StudentRead.model_validate(student)
    if student.school:
        result.school_name = student.school.sch_name
        result.state_name = student.school.state_name
    return result


@router.post("/", response_model=StudentRead)
async def create_student(
    student_data: StudentCreate,
    repo: IStudentRepository = Depends(get_student_repo)
):
    from app.domain.models.student import Student
    student = Student(**student_data.model_dump())
    created = await repo.add(student)
    return StudentRead.model_validate(created)


@router.put("/{student_id}", response_model=StudentRead)
async def update_student(
    student_id: UUID,
    student_data: StudentUpdate,
    repo: IStudentRepository = Depends(get_student_repo)
):
    student = await repo.get_by_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    for field, value in student_data.model_dump(exclude_unset=True).items():
        setattr(student, field, value)
    
    updated = await repo.update(student)
    return StudentRead.model_validate(updated)


@router.delete("/{student_id}")
async def delete_student(
    student_id: UUID,
    repo: IStudentRepository = Depends(get_student_repo)
):
    deleted = await repo.delete_by_id(student_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"message": "Student deleted"}


@router.delete("/")
async def delete_all_students(
    force: bool = Query(False),
    repo: IStudentRepository = Depends(get_student_repo),
    session: AsyncSession = Depends(get_db)
):
    if not force:
        raise HTTPException(status_code=400, detail="Add ?force=true to confirm deletion")
    
    async with session.begin():
        count = await repo.delete_all()
    return {"deleted": count}


@router.get("/by-state/{state_code}", response_model=List[StudentWithSchoolDetails])
async def get_students_by_state(
    state_code: str,
    batch: Optional[str] = None,
    session: AsyncSession = Depends(get_db)
):
    from app.domain.models.student import Student
    from app.domain.models.school import School
    from app.core.config import settings
    from pathlib import Path
    import os
    
    query = (
        select(Student, School)
        .join(School, Student.school_id == School.id, isouter=True)
        .where(School.state == state_code)
    )
    
    # Filter by batch if provided
    if batch:
        query = query.where(Student.batch == batch)
    
    result = await session.execute(query)
    rows = result.all()
    
    students_data = []
    for student, school in rows:
        photo_url = "/media/null_passport.jpg"
        if student.photo_path and os.path.exists(student.photo_path):
            path_obj = Path(student.photo_path)
            try:
                relative = path_obj.relative_to(settings.media_root)
                photo_url = f"/media/{relative.as_posix()}"
            except ValueError:
                pass

        students_data.append(StudentWithSchoolDetails(
            reg_no=student.reg_no,
            cand_name=student.cand_name,
            ser_no=student.ser_no,
            sch_name=school.sch_name if school else None,
            schnum=student.schnum,
            town=school.town if school else None,
            custodian=school.custodian if school else None,
            photo_url=photo_url,
            batch=student.batch
        ))
    
    return students_data