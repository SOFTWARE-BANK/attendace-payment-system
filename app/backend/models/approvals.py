from core.database import Base
from datetime import datetime
from sqlalchemy import Column, Date, DateTime, Integer, String


class Approvals(Base):
    __tablename__ = "approvals"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    doc_no = Column(String, nullable=True)
    doc_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    target_date = Column(Date, nullable=True)
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)
    emp_no = Column(String, nullable=True)
    department = Column(String, nullable=True)
    requester_emp_no = Column(String, nullable=True)
    requester_name = Column(String, nullable=True)
    current_step = Column(String, nullable=True)
    status = Column(String, nullable=True)
    hr_approver = Column(String, nullable=True)
    hr_approved_at = Column(DateTime(timezone=True), nullable=True)
    hr_comment = Column(String, nullable=True)
    manager_approver = Column(String, nullable=True)
    manager_approved_at = Column(DateTime(timezone=True), nullable=True)
    manager_comment = Column(String, nullable=True)
    ceo_approver = Column(String, nullable=True)
    ceo_approved_at = Column(DateTime(timezone=True), nullable=True)
    ceo_comment = Column(String, nullable=True)
    rejected_by = Column(String, nullable=True)
    reject_reason = Column(String, nullable=True)
    record_count = Column(Integer, nullable=True)
    summary = Column(String, nullable=True)
    payload = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)