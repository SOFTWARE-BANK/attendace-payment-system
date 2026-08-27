"""전자결재 워크플로우 서비스.

근태담당자(HR) -> 부서장(Manager) -> CEO 3단계 결재를 처리한다.
문서 유형: daily_close(일일마감), weekend_work(휴일근무), leave_request(휴가품의),
overtime_convert(연장근무 휴가전환).
"""

import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from models.approvals import Approvals
from models.daily_attendances import Daily_attendances
from models.employees import Employees
from models.leave_balances import Leave_balances
from models.leave_requests import Leave_requests
from models.overtime_banks import Overtime_banks
from models.weekend_work_requests import Weekend_work_requests

logger = logging.getLogger(__name__)

STEP_ORDER = ["hr", "manager", "ceo"]
STEP_LABEL = {"hr": "근태담당자", "manager": "부서장", "ceo": "CEO", "completed": "완료", "rejected": "반려"}


class ApprovalFlowService:
    """3단계 전자결재 상태 전이를 관리한다."""

    def __init__(self, db):
        self.db = db

    async def _actor(self, emp_no: Optional[str]) -> Optional[Employees]:
        if not emp_no:
            return None
        result = await self.db.execute(select(Employees).where(Employees.emp_no == emp_no))
        return result.scalars().first()

    @staticmethod
    def _doc_no(doc_type: str) -> str:
        prefix = {
            "daily_close": "ATT",
            "weekend_work": "HWD",
            "leave_request": "LEV",
            "overtime_convert": "OTC",
        }.get(doc_type, "DOC")
        return f"{prefix}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # ------------------------------------------------------------- 상신
    async def submit_daily_close(
        self, work_date: date, requester_emp_no: str, department: Optional[str] = None
    ) -> Dict[str, Any]:
        """일일 근태 마감 결재를 상신한다."""
        stmt = select(Daily_attendances).where(Daily_attendances.work_date == work_date)
        if department:
            stmt = stmt.where(Daily_attendances.department == department)
        result = await self.db.execute(stmt)
        records = [r for r in result.scalars().all() if not r.locked and r.confirm_status in ("draft", "rejected")]
        if not records:
            raise ValueError("상신 가능한 근태 레코드가 없습니다. 먼저 근태 정산을 실행하세요.")

        requester = await self._actor(requester_emp_no)
        late_cnt = sum(1 for r in records if (r.late_minutes or 0) > 0)
        absent_cnt = sum(1 for r in records if r.status == "absent")
        overtime = sum((r.overtime_minutes or 0) for r in records)

        doc = Approvals(
            doc_no=self._doc_no("daily_close"),
            doc_type="daily_close",
            title=f"{work_date.isoformat()} 일일 근태 마감{f' ({department})' if department else ''}",
            target_date=work_date,
            period_start=work_date,
            period_end=work_date,
            department=department,
            requester_emp_no=requester_emp_no,
            requester_name=requester.name if requester else requester_emp_no,
            current_step="manager",
            status="pending",
            hr_approver=requester.name if requester else requester_emp_no,
            hr_approved_at=datetime.now(),
            hr_comment="근태담당자 정산 완료 후 상신",
            record_count=len(records),
            summary=f"대상 {len(records)}건 · 지각 {late_cnt}건 · 결근 {absent_cnt}건 · 연장 {overtime}분",
            payload=json.dumps({"attendance_ids": [r.id for r in records]}, ensure_ascii=False),
        )
        self.db.add(doc)
        await self.db.commit()
        doc_id = doc.id

        for r in records:
            r.confirm_status = "submitted"
            r.approval_id = doc_id
        await self.db.commit()
        return {"approval_id": doc_id, "doc_no": doc.doc_no, "record_count": len(records), "current_step": "manager"}

    async def submit_request(self, doc_type: str, entity_id: int, requester_emp_no: str) -> Dict[str, Any]:
        """휴가품의/휴일근무/연장전환 신청 문서를 결재 상신한다."""
        requester = await self._actor(requester_emp_no)
        requester_name = requester.name if requester else requester_emp_no

        if doc_type == "leave_request":
            entity = await self.db.get(Leave_requests, entity_id)
            if entity is None:
                raise ValueError("휴가 품의를 찾을 수 없습니다.")
            title = f"휴가 품의 - {entity.employee_name} ({entity.start_date} ~ {entity.end_date})"
            summary = f"{entity.leave_type} {entity.days}일 · 사유: {entity.reason or '-'}"
            emp_no, department = entity.emp_no, entity.department
            period_start, period_end, target_date = entity.start_date, entity.end_date, entity.start_date
        elif doc_type == "weekend_work":
            entity = await self.db.get(Weekend_work_requests, entity_id)
            if entity is None:
                raise ValueError("휴일근무 신청을 찾을 수 없습니다.")
            title = f"휴일근무 신청 - {entity.employee_name} ({entity.work_date})"
            summary = (
                f"{entity.day_type} {entity.planned_start}~{entity.planned_end} "
                f"({entity.planned_minutes or 0}분, 가산율 {entity.premium_rate or 1.5})"
            )
            emp_no, department = entity.emp_no, entity.department
            period_start = period_end = target_date = entity.work_date
        elif doc_type == "overtime_convert":
            entity = await self.db.get(Overtime_banks, entity_id)
            if entity is None:
                raise ValueError("연장근무 전환 신청을 찾을 수 없습니다.")
            title = f"연장근무 휴가전환 - {entity.employee_name}"
            summary = f"{abs(entity.minutes or 0)}분 → 휴가 {entity.target_leave_days or 0}일 전환"
            emp_no, department = entity.emp_no, entity.department
            period_start = period_end = target_date = entity.txn_date
        else:
            raise ValueError(f"지원하지 않는 문서 유형입니다: {doc_type}")

        doc = Approvals(
            doc_no=self._doc_no(doc_type),
            doc_type=doc_type,
            title=title,
            target_date=target_date,
            period_start=period_start,
            period_end=period_end,
            emp_no=emp_no,
            department=department,
            requester_emp_no=requester_emp_no,
            requester_name=requester_name,
            current_step="hr",
            status="pending",
            record_count=1,
            summary=summary,
            payload=json.dumps({"entity_id": entity_id, "doc_type": doc_type}, ensure_ascii=False),
        )
        self.db.add(doc)
        await self.db.commit()
        doc_id = doc.id

        entity.status = "pending"
        entity.approval_id = doc_id
        await self.db.commit()
        return {"approval_id": doc_id, "doc_no": doc.doc_no, "current_step": "hr"}

    # ------------------------------------------------------------- 승인/반려
    async def approve(self, approval_id: int, actor_emp_no: str, comment: str = "") -> Dict[str, Any]:
        """현재 결재 단계를 승인하고 다음 단계로 진행한다."""
        doc = await self.db.get(Approvals, approval_id)
        if doc is None:
            raise ValueError("결재 문서를 찾을 수 없습니다.")
        if doc.status != "pending":
            raise ValueError(f"이미 처리된 문서입니다. (상태: {doc.status})")

        actor = await self._actor(actor_emp_no)
        actor_name = actor.name if actor else actor_emp_no
        actor_role = (actor.role if actor else "employee") or "employee"
        step = doc.current_step or "hr"

        allowed = {"hr": {"hr", "ceo"}, "manager": {"manager", "ceo"}, "ceo": {"ceo"}}
        if actor_role not in allowed.get(step, set()):
            raise ValueError(f"{STEP_LABEL.get(step, step)} 단계는 해당 권한으로 승인할 수 없습니다.")

        now = datetime.now()
        if step == "hr":
            doc.hr_approver = actor_name
            doc.hr_approved_at = now
            doc.hr_comment = comment or "근태담당자 승인"
            doc.current_step = "manager"
        elif step == "manager":
            doc.manager_approver = actor_name
            doc.manager_approved_at = now
            doc.manager_comment = comment or "부서장 승인"
            doc.current_step = "ceo"
        elif step == "ceo":
            doc.ceo_approver = actor_name
            doc.ceo_approved_at = now
            doc.ceo_comment = comment or "CEO 최종 승인"
            doc.current_step = "completed"
            doc.status = "approved"
        else:
            raise ValueError("진행 가능한 결재 단계가 없습니다.")

        next_step = doc.current_step
        doc_type = doc.doc_type
        payload = doc.payload
        await self.db.commit()

        applied: Dict[str, Any] = {}
        if next_step == "manager" and doc_type == "daily_close":
            await self._set_attendance_status(payload, "submitted")
        if next_step == "ceo" and doc_type == "daily_close":
            applied = await self._set_attendance_status(payload, "manager_approved")
        if doc.status == "approved":
            applied = await self._apply_final(doc_type, payload, approval_id, actor_name)

        return {
            "approval_id": approval_id,
            "status": doc.status,
            "current_step": next_step,
            "current_step_label": STEP_LABEL.get(next_step, next_step),
            "applied": applied,
        }

    async def reject(self, approval_id: int, actor_emp_no: str, reason: str) -> Dict[str, Any]:
        """결재를 반려하고 대상 레코드를 재작업 상태로 되돌린다."""
        doc = await self.db.get(Approvals, approval_id)
        if doc is None:
            raise ValueError("결재 문서를 찾을 수 없습니다.")
        if doc.status != "pending":
            raise ValueError("이미 처리된 문서입니다.")
        if not reason:
            raise ValueError("반려 사유를 입력하세요.")

        actor = await self._actor(actor_emp_no)
        doc.status = "rejected"
        doc.rejected_by = actor.name if actor else actor_emp_no
        doc.reject_reason = reason
        doc.current_step = "rejected"
        doc_type = doc.doc_type
        payload = doc.payload
        await self.db.commit()

        if doc_type == "daily_close":
            await self._set_attendance_status(payload, "rejected")
        else:
            await self._set_entity_status(doc_type, payload, "rejected")
        return {"approval_id": approval_id, "status": "rejected", "reason": reason}

    # --------------------------------------------------------- 내부 반영 처리
    async def _set_attendance_status(self, payload: Optional[str], status: str) -> Dict[str, Any]:
        ids = self._payload_ids(payload)
        if not ids:
            return {"updated": 0}
        result = await self.db.execute(select(Daily_attendances).where(Daily_attendances.id.in_(ids)))
        records = result.scalars().all()
        for r in records:
            r.confirm_status = status
            if status == "rejected":
                r.locked = False
        await self.db.commit()
        return {"updated": len(records), "confirm_status": status}

    @staticmethod
    def _payload_ids(payload: Optional[str]) -> List[int]:
        try:
            data = json.loads(payload) if payload else {}
        except (ValueError, TypeError):
            return []
        return [int(i) for i in data.get("attendance_ids", [])]

    @staticmethod
    def _payload_entity_id(payload: Optional[str]) -> Optional[int]:
        try:
            data = json.loads(payload) if payload else {}
        except (ValueError, TypeError):
            return None
        value = data.get("entity_id")
        return int(value) if value is not None else None

    async def _set_entity_status(self, doc_type: str, payload: Optional[str], status: str) -> None:
        entity_id = self._payload_entity_id(payload)
        if entity_id is None:
            return
        model = {
            "leave_request": Leave_requests,
            "weekend_work": Weekend_work_requests,
            "overtime_convert": Overtime_banks,
        }.get(doc_type)
        if model is None:
            return
        entity = await self.db.get(model, entity_id)
        if entity is not None:
            entity.status = status
            await self.db.commit()

    async def _apply_final(
        self, doc_type: str, payload: Optional[str], approval_id: int, actor_name: str
    ) -> Dict[str, Any]:
        """CEO 최종 승인 시 실제 업무 데이터를 반영한다."""
        if doc_type == "daily_close":
            ids = self._payload_ids(payload)
            if not ids:
                return {"locked": 0}
            result = await self.db.execute(select(Daily_attendances).where(Daily_attendances.id.in_(ids)))
            records = result.scalars().all()
            for r in records:
                r.confirm_status = "ceo_approved"
                r.locked = True
            await self.db.commit()
            return {"locked": len(records), "message": f"{len(records)}건 근태 확정 및 잠금 완료"}

        entity_id = self._payload_entity_id(payload)
        if entity_id is None:
            return {}

        if doc_type == "leave_request":
            return await self._apply_leave(entity_id, approval_id)
        if doc_type == "weekend_work":
            return await self._apply_weekend(entity_id)
        if doc_type == "overtime_convert":
            return await self._apply_convert(entity_id, actor_name)
        return {}

    async def _apply_leave(self, entity_id: int, approval_id: int) -> Dict[str, Any]:
        """휴가 승인 → 잔여 차감 + 해당 기간 근태에 휴가 반영."""
        entity = await self.db.get(Leave_requests, entity_id)
        if entity is None:
            return {}
        entity.status = "approved"

        year = entity.start_date.year
        result = await self.db.execute(
            select(Leave_balances)
            .where(Leave_balances.emp_no == entity.emp_no)
            .where(Leave_balances.year == year)
            .where(Leave_balances.leave_type == entity.leave_type)
        )
        balance = result.scalars().first()
        if balance is None:
            balance = Leave_balances(
                emp_no=entity.emp_no,
                employee_name=entity.employee_name,
                department=entity.department,
                year=year,
                leave_type=entity.leave_type,
                granted_days=0,
                used_days=0,
                pending_days=0,
                converted_days=0,
                note="승인 시 자동 생성",
            )
            self.db.add(balance)
        balance.used_days = float(balance.used_days or 0) + float(entity.days or 0)
        balance.pending_days = max(float(balance.pending_days or 0) - float(entity.days or 0), 0)

        reason_code = {"annual": "ANNUAL", "sick": "SICK", "converted": "CONVERTED_OFF"}.get(
            entity.leave_type, "ANNUAL"
        )
        result = await self.db.execute(
            select(Daily_attendances)
            .where(Daily_attendances.emp_no == entity.emp_no)
            .where(Daily_attendances.work_date >= entity.start_date)
            .where(Daily_attendances.work_date <= entity.end_date)
        )
        reflected = 0
        for r in result.scalars().all():
            if r.locked:
                continue
            r.status = "leave"
            r.reason_code = reason_code
            r.reason_note = f"휴가 품의 #{entity.id} 승인 반영"
            r.leave_request_id = entity.id
            r.late_minutes = 0
            r.early_leave_minutes = 0
            reflected += 1
        entity.reflected = True
        entity.reflected_count = reflected
        await self.db.commit()
        return {
            "leave_request_id": entity.id,
            "used_days": balance.used_days,
            "attendance_reflected": reflected,
            "message": f"휴가 {entity.days}일 승인 · 근태 {reflected}건 반영",
        }

    async def _apply_weekend(self, entity_id: int) -> Dict[str, Any]:
        """휴일근무 승인 → 실제 출입기록과 대조하여 근태에 휴일근무 반영."""
        entity = await self.db.get(Weekend_work_requests, entity_id)
        if entity is None:
            return {}
        entity.status = "approved"

        result = await self.db.execute(
            select(Daily_attendances)
            .where(Daily_attendances.emp_no == entity.emp_no)
            .where(Daily_attendances.work_date == entity.work_date)
        )
        record = result.scalars().first()
        matched = False
        actual_minutes = 0
        if record is not None and not record.locked:
            record.status = "holiday_work"
            record.reason_code = "HOLIDAY_WORK"
            record.reason_note = f"휴일근무 신청 #{entity.id} 승인 반영 (가산율 {entity.premium_rate or 1.5})"
            record.day_type = entity.day_type or record.day_type
            record.holiday_minutes = record.work_minutes or entity.planned_minutes or 0
            actual_minutes = record.holiday_minutes or 0
            entity.actual_start = record.check_in
            entity.actual_end = record.check_out
            entity.actual_minutes = actual_minutes
            matched = bool(record.check_in)
        entity.matched = matched
        await self.db.commit()
        return {
            "weekend_request_id": entity.id,
            "matched": matched,
            "actual_minutes": actual_minutes,
            "message": "휴일근무 확정" + ("" if matched else " (출입기록 미대조)"),
        }

    async def _apply_convert(self, entity_id: int, actor_name: str) -> Dict[str, Any]:
        """연장근무 → 휴가 전환 승인 시 휴가 잔여에 적립한다."""
        entity = await self.db.get(Overtime_banks, entity_id)
        if entity is None:
            return {}
        entity.status = "approved"
        entity.note = f"{entity.note or ''} / {actor_name} 최종승인".strip(" /")

        year = (entity.txn_date or date.today()).year
        result = await self.db.execute(
            select(Leave_balances)
            .where(Leave_balances.emp_no == entity.emp_no)
            .where(Leave_balances.year == year)
            .where(Leave_balances.leave_type == "converted")
        )
        balance = result.scalars().first()
        days = float(entity.target_leave_days or 0)
        if balance is None:
            balance = Leave_balances(
                emp_no=entity.emp_no,
                employee_name=entity.employee_name,
                department=entity.department,
                year=year,
                leave_type="converted",
                granted_days=days,
                used_days=0,
                pending_days=0,
                converted_days=days,
                note="연장근무 전환 적립",
            )
            self.db.add(balance)
        else:
            balance.granted_days = float(balance.granted_days or 0) + days
            balance.converted_days = float(balance.converted_days or 0) + days
        await self.db.commit()
        return {
            "overtime_bank_id": entity.id,
            "converted_days": days,
            "message": f"연장근무 {abs(entity.minutes or 0)}분 → 보상휴가 {days}일 적립",
        }

    # --------------------------------------------------------------- 조회
    async def inbox(self, actor_emp_no: str) -> Dict[str, Any]:
        """로그인 사용자 권한에 맞는 결재 대기 문서를 반환한다."""
        actor = await self._actor(actor_emp_no)
        role = (actor.role if actor else "employee") or "employee"
        step_map = {"hr": ["hr"], "manager": ["manager"], "ceo": ["ceo"]}
        steps = step_map.get(role, [])
        stmt = select(Approvals).where(Approvals.status == "pending").order_by(Approvals.id.desc())
        result = await self.db.execute(stmt)
        docs = result.scalars().all()
        pending = [d for d in docs if d.current_step in steps] if steps else []
        return {
            "role": role,
            "actor_name": actor.name if actor else actor_emp_no,
            "pending_count": len(pending),
            "pending_ids": [d.id for d in pending],
        }