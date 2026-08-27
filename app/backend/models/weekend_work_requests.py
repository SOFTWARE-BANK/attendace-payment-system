from core.database import Base
from datetime import datetime
from sqlalchemy import Boolean, Column, Date, DateTime, Float, Integer, String


class Weekend_work_requests(Base):
    __tablename__ = "weekend_work_requests"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    emp_no = Column(String, nullable=False)
    employee_name = Column(String, nullable=True)
    department = Column(String, nullable=True)
    work_date = Column(Date, nullable=False)
    day_type = Column(String, nullable=True)
    planned_start = Column(String, nullable=True)
    planned_end = Column(String, nullable=True)
    planned_minutes = Column(Integer, nullable=True)
    actual_start = Column(DateTime(timezone=True), nullable=True)
    actual_end = Column(DateTime(timezone=True), nullable=True)
    actual_minutes = Column(Integer, nullable=True)
    premium_rate = Column(Float, nullable=True)
    reason = Column(String, nullable=True)
    status = Column(String, nullable=True)
    approval_id = Column(Integer, index=True, nullable=True)
    matched = Column(Boolean, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)