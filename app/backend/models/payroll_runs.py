from core.database import Base
from datetime import datetime
from sqlalchemy import Boolean, Column, Date, DateTime, Float, Integer, String


class Payroll_runs(Base):
    __tablename__ = "payroll_runs"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    run_name = Column(String, nullable=False)
    pay_cycle = Column(String, nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    status = Column(String, nullable=True)
    employee_count = Column(Integer, nullable=True)
    total_amount = Column(Float, nullable=True)
    confirmed_only = Column(Boolean, nullable=True)
    calculated_at = Column(DateTime(timezone=True), nullable=True)
    note = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)