from core.database import Base
from datetime import datetime
from sqlalchemy import Column, Date, DateTime, Integer, String


class Access_logs(Base):
    __tablename__ = "access_logs"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    emp_no = Column(String, nullable=False)
    employee_name = Column(String, nullable=True)
    terminal_id = Column(String, index=True, nullable=True)
    device_name = Column(String, nullable=True)
    event_time = Column(DateTime(timezone=True), nullable=False)
    event_date = Column(Date, nullable=True)
    event_type = Column(String, nullable=True)
    auth_mode = Column(String, nullable=True)
    source = Column(String, nullable=True)
    raw_payload = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)