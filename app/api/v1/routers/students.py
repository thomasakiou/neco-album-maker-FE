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
        items.append(item)
    
    return PaginatedResponse(total=total, page=page, limit=limit, items=items)


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
    
    result = await session.execute(query)
    rows = result.all()
    
    null_passport = str(Path(settings.media_root) / "null_passport.jpg")
    
    students_data = []
    for student, school in rows:
        photo_path = student.photo_path
        if not photo_path or not os.path.exists(photo_path):
            photo_path = null_passport
        
        students_data.append(StudentWithSchoolDetails(
            reg_no=student.reg_no,
            cand_name=student.cand_name,
            ser_no=student.ser_no,
            sch_name=school.sch_name if school else None,
            schnum=student.schnum,
            town=school.town if school else None,
            custodian=school.custodian if school else None,
            photo_url=photo_path
        ))
    
    return students_data