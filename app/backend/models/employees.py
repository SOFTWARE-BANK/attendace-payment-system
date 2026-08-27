from core.database import Base
from datetime import datetime
from sqlalchemy import Boolean, Column, Date, DateTime, Float, Integer, String


class Employees(Base):
    __tablename__ = "employees"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    emp_no = Column(String, nullable=False)
    name = Column(String, nullable=False)
    department = Column(String, nullable=False)
    position = Column(String, nullable=True)
    role = Column(String, nullable=True)
    email = Column(String, nullable=True)
    pay_type = Column(String, nullable=True)
    hourly_rate = Column(Float, nullable=True)
    monthly_salary = Column(Float, nullable=True)
    pay_cycle = Column(String, nullable=True)
    std_start = Column(String, nullable=True)
    std_end = Column(String, nullable=True)
    break_minutes = Column(Integer, nullable=True)
    grace_minutes = Column(Integer, nullable=True)
    hire_date = Column(Date, nullable=True)
    annual_leave_days = Column(Float, nullable=True)
    terminal_user_id = Column(String, index=True, nullable=True)
    manager_emp_no = Column(String, nullable=True)
    active = Column(Boolean, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)