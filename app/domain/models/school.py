from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

import uuid
from app.core.db import Base


class School(Base):
    __tablename__ = "schools"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    schnum = Column(String, unique=True, nullable=False, index=True)
    sch_name = Column(String, nullable=False)
    state = Column(String, ForeignKey("states.code"), nullable=False)
    state_name = Column(String, nullable=False)
    custodian = Column(String, nullable=True)
    town = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    state_details = relationship("State", backref="school_list")