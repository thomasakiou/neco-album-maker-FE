from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.core.db import Base


class Student(Base):
    __tablename__ = "students"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch = Column(String, nullable=False)
    schnum = Column(String, nullable=False)
    sch_name = Column(String, nullable=True)
    reg_no = Column(String, unique=True, nullable=False, index=True)
    ser_no = Column(String, nullable=False)
    cand_name = Column(String, nullable=False)
    school_id = Column(UUID(as_uuid=True), ForeignKey("schools.id"), nullable=True)
    photo_path = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    school = relationship("School", backref="students")
    
    __table_args__ = (
        Index('idx_batch_school_reg', 'batch', 'schnum', 'reg_no'),
    )