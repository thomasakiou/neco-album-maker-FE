from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.school_schema import SchoolRead, SchoolCreate, SchoolUpdate
from app.domain.repositories.interfaces import ISchoolRepository
from app.api.v1.deps import get_school_repo
from app.core.db import get_db

router = APIRouter(prefix="/schools", tags=["schools"])


@router.get("/", response_model=List[SchoolRead])
async def list_schools(
    schnum: Optional[str] = None,
    state: Optional[str] = None,
    sch_name: Optional[str] = None,
    repo: ISchoolRepository = Depends(get_school_repo)
):
    schools = await repo.find_all(schnum, state, sch_name)
    return [SchoolRead.model_validate(school) for school in schools]


@router.get("/{school_id}", response_model=SchoolRead)
async def get_school(
    school_id: UUID,
    repo: ISchoolRepository = Depends(get_school_repo)
):
    school = await repo.get_by_id(school_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    return SchoolRead.model_validate(school)


@router.post("/", response_model=SchoolRead)
async def create_school(
    school_data: SchoolCreate,
    repo: ISchoolRepository = Depends(get_school_repo)
):
    from app.domain.models.school import School
    school = School(**school_data.model_dump())
    created = await repo.add(school)
    return SchoolRead.model_validate(created)


@router.put("/{school_id}", response_model=SchoolRead)
async def update_school(
    school_id: UUID,
    school_data: SchoolUpdate,
    repo: ISchoolRepository = Depends(get_school_repo)
):
    school = await repo.get_by_id(school_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    for field, value in school_data.model_dump(exclude_unset=True).items():
        setattr(school, field, value)
    
    updated = await repo.update(school)
    return SchoolRead.model_validate(updated)


@router.delete("/{school_id}")
async def delete_school(
    school_id: UUID,
    repo: ISchoolRepository = Depends(get_school_repo)
):
    deleted = await repo.delete_by_id(school_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="School not found")
    return {"message": "School deleted"}


@router.delete("/")
async def delete_all_schools(
    force: bool = Query(False),
    repo: ISchoolRepository = Depends(get_school_repo),
    session: AsyncSession = Depends(get_db)
):
    if not force:
        raise HTTPException(status_code=400, detail="Add ?force=true to confirm deletion")
    
    from sqlalchemy import delete
    from app.domain.models.student import Student
    
    async with session.begin():
        await session.execute(delete(Student))
        count = await repo.delete_all()
    return {"deleted": count}