from pydantic import BaseModel
from datetime import datetime


class StateBase(BaseModel):
    code: str
    state: str


class StateCreate(StateBase):
    pass


class StateUpdate(BaseModel):
    state: str


class StateRead(StateBase):
    schools: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
