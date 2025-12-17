from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class SchoolBase(BaseModel):
    schnum: str
    sch_name: str
    state: str
    state_name: str
    custodian: str | None = None
    town: str | None = None


class SchoolCreate(SchoolBase):
    pass


class SchoolUpdate(BaseModel):
    sch_name: str | None = None
    state: str | None = None
    state_name: str | None = None
    custodian: str | None = None
    town: str | None = None


class SchoolRead(SchoolBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
