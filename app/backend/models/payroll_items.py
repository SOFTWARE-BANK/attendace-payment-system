from core.database import Base
from datetime import datetime
from sqlalchemy import Column, Date, DateTime, Float, Integer, String


class Payroll_items(Base):
    __tablename__ = "payroll_items"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    payroll_run_id = Column(Integer, index=True, nullable=True)
    emp_no = Column(String, nullable=False)
    employee_name = Column(String, nullable=True)
    department = Column(String, nullable=True)
    pay_cycle = Column(String, nullable=True)
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)
    regular_minutes = Column(Integer, nullable=True)
    overtime_minutes = Column(Integer, nullable=True)
    holiday_minutes = Column(Integer, nullable=True)
    night_minutes = Column(Integer, nullable=True)
    late_minutes = Column(Integer, nullable=True)
    offset_minutes = Column(Integer, nullable=True)
    absent_days = Column(Float, nullable=True)
    leave_days = Column(Float, nullable=True)
    work_days = Column(Integer, nullable=True)
    confirmed_days = Column(Integer, nullable=True)
    base_pay = Column(Float, nullable=True)
    overtime_pay = Column(Float, nullable=True)
    holiday_pay = Column(Float, nullable=True)
    night_pay = Column(Float, nullable=True)
    late_deduction = Column(Float, nullable=True)
    offset_credit = Column(Float, nullable=True)
    absent_deduction = Column(Float, nullable=True)
    gross_pay = Column(Float, nullable=True)
    net_pay = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)