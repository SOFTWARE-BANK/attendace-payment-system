from core.database import Base
from datetime import datetime
from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String


class Daily_attendances(Base):
    __tablename__ = "daily_attendances"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    emp_no = Column(String, nullable=False)
    employee_name = Column(String, nullable=True)
    department = Column(String, nullable=True)
    work_date = Column(Date, nullable=False)
    day_type = Column(String, nullable=True)
    raw_check_in = Column(DateTime(timezone=True), nullable=True)
    raw_check_out = Column(DateTime(timezone=True), nullable=True)
    check_in = Column(DateTime(timezone=True), nullable=True)
    check_out = Column(DateTime(timezone=True), nullable=True)
    log_count = Column(Integer, nullable=True)
    scheduled_minutes = Column(Integer, nullable=True)
    work_minutes = Column(Integer, nullable=True)
    overtime_minutes = Column(Integer, nullable=True)
    night_minutes = Column(Integer, nullable=True)
    holiday_minutes = Column(Integer, nullable=True)
    late_minutes = Column(Integer, nullable=True)
    early_leave_minutes = Column(Integer, nullable=True)
    offset_minutes = Column(Integer, nullable=True)
    status = Column(String, nullable=True)
    reason_code = Column(String, nullable=True)
    reason_note = Column(String, nullable=True)
    adjusted = Column(Boolean, nullable=True)
    adjusted_by = Column(String, nullable=True)
    adjust_history = Column(String, nullable=True)
    confirm_status = Column(String, nullable=True)
    approval_id = Column(Integer, index=True, nullable=True)
    leave_request_id = Column(Integer, index=True, nullable=True)
    locked = Column(Boolean, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)