from core.database import Base
from datetime import datetime
from sqlalchemy import Column, Date, DateTime, Float, Integer, String


class Overtime_banks(Base):
    __tablename__ = "overtime_banks"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    emp_no = Column(String, nullable=False)
    employee_name = Column(String, nullable=True)
    department = Column(String, nullable=True)
    txn_type = Column(String, nullable=False)
    txn_date = Column(Date, nullable=True)
    source_date = Column(Date, nullable=True)
    minutes = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=True)
    target_leave_days = Column(Float, nullable=True)
    target_attendance_id = Column(Integer, index=True, nullable=True)
    status = Column(String, nullable=True)
    approval_id = Column(Integer, index=True, nullable=True)
    note = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)