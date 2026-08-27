from core.database import Base
from datetime import datetime
from sqlalchemy import Column, DateTime, Float, Integer, String


class Leave_balances(Base):
    __tablename__ = "leave_balances"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    emp_no = Column(String, nullable=False)
    employee_name = Column(String, nullable=True)
    department = Column(String, nullable=True)
    year = Column(Integer, nullable=False)
    leave_type = Column(String, nullable=False)
    granted_days = Column(Float, nullable=True)
    used_days = Column(Float, nullable=True)
    pending_days = Column(Float, nullable=True)
    converted_days = Column(Float, nullable=True)
    note = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)