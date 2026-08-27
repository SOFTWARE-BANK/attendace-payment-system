from core.database import Base
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String


class Attendance_reasons(Base):
    __tablename__ = "attendance_reasons"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, nullable=True)
    pay_effect = Column(String, nullable=True)
    deduct_rate = Column(Float, nullable=True)
    requires_approval = Column(Boolean, nullable=True)
    offsettable = Column(Boolean, nullable=True)
    sort_order = Column(Integer, nullable=True)
    description = Column(String, nullable=True)
    active = Column(Boolean, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)