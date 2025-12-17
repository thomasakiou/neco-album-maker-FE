from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy import select, delete, update, func, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.domain.models.student import Student
from app.domain.models.school import School
from app.domain.models.state import State
from app.domain.repositories.interfaces import (
    IStudentRepository, ISchoolRepository, IStateRepository, StudentFilter
)


class StudentRepository(IStudentRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def add(self, student: Student) -> Student:
        self.session.add(student)
        await self.session.flush()
        return student
    
    async def bulk_add(self, students: List[Student]) -> int:
        self.session.add_all(students)
        await self.session.flush()
        return len(students)
    
    async def get_by_id(self, id: UUID) -> Optional[Student]:
        result = await self.session.execute(
            select(Student).options(selectinload(Student.school)).where(Student.id == id)
        )
        return result.scalar_one_or_none()
    
    async def find(self, filters: StudentFilter, limit: int, offset: int) -> Tuple[int, List[Student]]:
        query = select(Student).join(School, Student.school_id == School.id, isouter=True)
        
        if filters.schnum:
            query = query.where(Student.schnum == filters.schnum)
        if filters.sch_name:
            query = query.where(School.sch_name.ilike(f"%{filters.sch_name}%"))
        if filters.batch:
            query = query.where(Student.batch == filters.batch)
        if filters.state_name:
            query = query.where(School.state_name.ilike(f"%{filters.state_name}%"))
        if filters.cand_name:
            query = query.where(Student.cand_name.ilike(f"%{filters.cand_name}%"))
        if filters.reg_no:
            query = query.where(Student.reg_no.ilike(f"%{filters.reg_no}%"))
        
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.session.scalar(count_query)
        
        query = query.options(selectinload(Student.school)).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return total or 0, result.scalars().all()
    
    async def delete_all(self) -> int:
        result = await self.session.execute(delete(Student))
        return result.rowcount
    
    async def update(self, student: Student) -> Student:
        await self.session.flush()
        return student
    
    async def delete_by_id(self, id: UUID) -> bool:
        result = await self.session.execute(delete(Student).where(Student.id == id))
        return result.rowcount > 0


class SchoolRepository(ISchoolRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def add(self, school: School) -> School:
        self.session.add(school)
        await self.session.flush()
        return school
    
    async def bulk_upsert(self, schools: List[School], valid_state_codes: set = None) -> int:
        if not schools:
            return 0
        
        if valid_state_codes:
            schools = [s for s in schools if s.state in valid_state_codes]
        
        if not schools:
            return 0
        
        # Batch insert to avoid parameter limit (32767 / 7 columns ≈ 4681 rows max)
        batch_size = 1000
        total_inserted = 0
        
        for i in range(0, len(schools), batch_size):
            batch = schools[i:i + batch_size]
            values = [
                {
                    "id": s.id,
                    "schnum": s.schnum,
                    "sch_name": s.sch_name,
                    "state": s.state,
                    "state_name": s.state_name,
                    "custodian": s.custodian,
                    "town": s.town
                }
                for s in batch
            ]
            
            stmt = pg_insert(School.__table__).values(values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["schnum"],
                set_={
                    "sch_name": stmt.excluded.sch_name,
                    "state": stmt.excluded.state,
                    "state_name": stmt.excluded.state_name,
                    "custodian": stmt.excluded.custodian,
                    "town": stmt.excluded.town
                }
            )
            await self.session.execute(stmt)
            total_inserted += len(batch)
        
        return total_inserted
    
    async def get_by_id(self, id: UUID) -> Optional[School]:
        result = await self.session.execute(select(School).where(School.id == id))
        return result.scalar_one_or_none()
    
    async def get_by_schnum(self, schnum: str) -> Optional[School]:
        result = await self.session.execute(select(School).where(School.schnum == schnum))
        return result.scalar_one_or_none()
    
    async def find_all(self, schnum: Optional[str] = None, state: Optional[str] = None,
                      sch_name: Optional[str] = None) -> List[School]:
        query = select(School)
        
        if schnum:
            query = query.where(School.schnum == schnum)
        if state:
            query = query.where(School.state == state)
        if sch_name:
            query = query.where(School.sch_name.ilike(f"%{sch_name}%"))
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def delete_all(self) -> int:
        result = await self.session.execute(delete(School))
        return result.rowcount
    
    async def update(self, school: School) -> School:
        await self.session.flush()
        return school
    
    async def delete_by_id(self, id: UUID) -> bool:
        result = await self.session.execute(delete(School).where(School.id == id))
        return result.rowcount > 0


class StateRepository(IStateRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def add(self, state: State) -> State:
        self.session.add(state)
        await self.session.flush()
        return state
    
    async def bulk_upsert(self, states: List[State]) -> int:
        if not states:
            return 0
        
        values = [{"code": s.code, "state": s.state, "schools": s.schools} for s in states]
        
        stmt = pg_insert(State).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["code"],
            set_={"state": stmt.excluded.state, "schools": stmt.excluded.schools}
        )
        await self.session.execute(stmt)
        return len(states)
    
    async def get_by_code(self, code: str) -> Optional[State]:
        result = await self.session.execute(select(State).where(State.code == code))
        return result.scalar_one_or_none()
    
    async def find_all(self) -> List[State]:
        result = await self.session.execute(select(State))
        return result.scalars().all()
    
    async def delete_all(self) -> int:
        result = await self.session.execute(delete(State))
        return result.rowcount
    
    async def update(self, state: State) -> State:
        await self.session.flush()
        return state
    
    async def delete_by_code(self, code: str) -> bool:
        result = await self.session.execute(delete(State).where(State.code == code))
        return result.rowcount > 0
