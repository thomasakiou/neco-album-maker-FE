from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.infra.repositories.sqlalchemy_repositories import (
    StudentRepository, SchoolRepository, StateRepository
)
from app.domain.repositories.interfaces import (
    IStudentRepository, ISchoolRepository, IStateRepository
)


async def get_student_repo(session: AsyncSession = Depends(get_db)) -> IStudentRepository:
    return StudentRepository(session)


async def get_school_repo(session: AsyncSession = Depends(get_db)) -> ISchoolRepository:
    return SchoolRepository(session)


async def get_state_repo(session: AsyncSession = Depends(get_db)) -> IStateRepository:
    return StateRepository(session)