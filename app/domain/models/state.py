from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.sql import func
from app.core.db import Base


class State(Base):
    __tablename__ = "states"
    
    code = Column(String, primary_key=True)
    state = Column(String, nullable=False)
    schools = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())