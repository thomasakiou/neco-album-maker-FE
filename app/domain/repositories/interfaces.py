from abc import ABC, abstractmethod
from typing import Optional, List, Tuple
from uuid import UUID
from app.domain.models.student import Student
from app.domain.models.school import School
from app.domain.models.state import State


class StudentFilter:
    def __init__(self, schnum: Optional[str] = None, sch_name: Optional[str] = None, 
                 batch: Optional[str] = None, state_name: Optional[str] = None, 
                 cand_name: Optional[str] = None, reg_no: Optional[str] = None):
        self.schnum = schnum
        self.sch_name = sch_name
        self.batch = batch
        self.state_name = state_name
        self.cand_name = cand_name
        self.reg_no = reg_no


class IStudentRepository(ABC):
    @abstractmethod
    async def add(self, student: Student) -> Student:
        pass
    
    @abstractmethod
    async def bulk_add(self, students: List[Student]) -> int:
        pass
    
    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[Student]:
        pass
    
    @abstractmethod
    async def find(self, filters: StudentFilter, limit: int, offset: int) -> Tuple[int, List[Student]]:
        pass
    
    @abstractmethod
    async def delete_all(self) -> int:
        pass
    
    @abstractmethod
    async def update(self, student: Student) -> Student:
        pass
    
    @abstractmethod
    async def delete_by_id(self, id: UUID) -> bool:
        pass


class ISchoolRepository(ABC):
    @abstractmethod
    async def add(self, school: School) -> School:
        pass
    
    @abstractmethod
    async def bulk_upsert(self, schools: List[School], valid_state_codes: set = None) -> int:
        pass
    
    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[School]:
        pass
    
    @abstractmethod
    async def get_by_schnum(self, schnum: str) -> Optional[School]:
        pass
    
    @abstractmethod
    async def find_all(self, schnum: Optional[str] = None, state: Optional[str] = None, 
                      sch_name: Optional[str] = None) -> List[School]:
        pass
    
    @abstractmethod
    async def delete_all(self) -> int:
        pass
    
    @abstractmethod
    async def update(self, school: School) -> School:
        pass
    
    @abstractmethod
    async def delete_by_id(self, id: UUID) -> bool:
        pass


class IStateRepository(ABC):
    @abstractmethod
    async def add(self, state: State) -> State:
        pass
    
    @abstractmethod
    async def bulk_upsert(self, states: List[State]) -> int:
        pass
    
    @abstractmethod
    async def get_by_code(self, code: str) -> Optional[State]:
        pass
    
    @abstractmethod
    async def find_all(self) -> List[State]:
        pass
    
    @abstractmethod
    async def delete_all(self) -> int:
        pass
    
    @abstractmethod
    async def update(self, state: State) -> State:
        pass
    
    @abstractmethod
    async def delete_by_code(self, code: str) -> bool:
        pass