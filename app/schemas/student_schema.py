from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional


class StudentBase(BaseModel):
    batch: str
    schnum: str
    sch_name: str | None = None
    reg_no: str
    ser_no: str
    cand_name: str


class StudentCreate(StudentBase):
    school_id: Optional[UUID] = None


class StudentUpdate(BaseModel):
    batch: str | None = None
    schnum: str | None = None
    sch_name: str | None = None
    reg_no: str | None = None
    ser_no: str | None = None
    cand_name: str | None = None
    school_id: UUID | None = None


class StudentRead(StudentBase):
    id: UUID
    school_id: Optional[UUID]
    school_name: Optional[str] = None
    state_name: Optional[str] = None
    photo_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PaginatedResponse(BaseModel):
    total: int
    page: int
    limit: int
    items: list
