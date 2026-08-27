from core.database import Base
from datetime import datetime
from sqlalchemy import Boolean, Column, Date, DateTime, Float, Integer, String


class Leave_requests(Base):
    __tablename__ = "leave_requests"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    emp_no = Column(String, nullable=False)
    employee_name = Column(String, nullable=True)
    department = Column(String, nullable=True)
    leave_type = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days = Column(Float, nullable=True)
    half_day_type = Column(String, nullable=True)
    reason = Column(String, nullable=True)
    status = Column(String, nullable=True)
    approval_id = Column(Integer, index=True, nullable=True)
    reflected = Column(Boolean, nullable=True)
    reflected_count = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)