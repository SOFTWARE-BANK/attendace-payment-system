"""근태 집계 엔진.

Hikvision 얼굴인식 단말기의 원시 출입기록(access_logs)에서 일자별 출근/퇴근 시간을
자동 추출하고, 지각/조퇴/연장/휴일/야간 시간을 계산하여 daily_attendances에 정산한다.
"""

import json
import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from models.access_logs import Access_logs
from models.attendance_reasons import Attendance_reasons
from models.daily_attendances import Daily_attendances
from models.employees import Employees
from models.leave_requests import Leave_requests
from models.overtime_banks import Overtime_banks
from models.weekend_work_requests import Weekend_work_requests

logger = logging.getLogger(__name__)

NIGHT_START = 22  # 야간근무 시작 (22시)
NIGHT_END = 6  # 야간근무 종료 (06시)
DEFAULT_HOLIDAY_PREMIUM = 1.5


def parse_hhmm(value: Optional[str], fallback: str) -> time:
    """'HH:MM' 문자열을 time 객체로 변환한다."""
    raw = (value or fallback or "09:00").strip()
    try:
        parts = raw.split(":")
        return time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
    except (ValueError, IndexError):
        hh, mm = fallback.split(":")
        return time(int(hh), int(mm))


def to_naive(value: Optional[datetime]) -> Optional[datetime]:
    """timezone 정보를 제거해 계산을 단순화한다."""
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def as_utc(value: Optional[datetime]) -> Optional[datetime]:
    """저장 시 타임존 재해석을 막기 위해 벽시계 시각을 UTC 라벨로 고정한다."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def day_type_of(work_date: date) -> str:
    """요일 기준 근무일 유형을 판정한다."""
    weekday = work_date.weekday()
    if weekday == 5:
        return "saturday"
    if weekday == 6:
        return "sunday"
    return "weekday"


def night_minutes_between(start: datetime, end: datetime) -> int:
    """22시~06시 구간에 포함된 야간 근무 분을 계산한다."""
    if not start or not end or end <= start:
        return 0
    total = 0
    cursor = start
    while cursor < end:
        nxt = min(cursor + timedelta(minutes=1), end)
        hour = cursor.hour
        if hour >= NIGHT_START or hour < NIGHT_END:
            total += int((nxt - cursor).total_seconds() // 60)
        cursor = nxt
    return total


class AttendanceEngine:
    """근태 정산 및 급여 집계 계산 엔진."""

    def __init__(self, db):
        self.db = db

    # ------------------------------------------------------------------ 조회
    async def load_employees(self, emp_nos: Optional[List[str]] = None) -> Dict[str, Employees]:
        stmt = select(Employees)
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        mapping = {row.emp_no: row for row in rows if row.active is not False}
        if emp_nos:
            mapping = {k: v for k, v in mapping.items() if k in emp_nos}
        return mapping

    async def load_reasons(self) -> Dict[str, Attendance_reasons]:
        result = await self.db.execute(select(Attendance_reasons))
        return {row.code: row for row in result.scalars().all()}

    # -------------------------------------------------------- 출퇴근 자동추출
    async def extract_pairs(self, work_date: date) -> Dict[str, Dict[str, Any]]:
        """당일 원시 출입기록에서 사번별 최초 입장/최종 퇴장을 추출한다."""
        start = datetime.combine(work_date, time(0, 0))
        end = start + timedelta(days=1)
        stmt = (
            select(Access_logs)
            .where(Access_logs.event_time >= start)
            .where(Access_logs.event_time < end)
            .order_by(Access_logs.event_time.asc())
        )
        result = await self.db.execute(stmt)
        logs = result.scalars().all()

        grouped: Dict[str, Dict[str, Any]] = {}
        for log in logs:
            event_time = to_naive(log.event_time)
            if event_time is None:
                continue
            bucket = grouped.setdefault(
                log.emp_no,
                {"first_in": None, "last_out": None, "count": 0, "name": log.employee_name},
            )
            bucket["count"] += 1
            etype = (log.event_type or "ACCESS").upper()
            # IN 이벤트가 있으면 최초 IN, 없으면 전체 기록의 최초 시각을 출근으로 본다
            if etype == "IN" or bucket["first_in"] is None:
                if bucket["first_in"] is None or event_time < bucket["first_in"]:
                    if etype != "OUT" or bucket["first_in"] is None:
                        bucket["first_in"] = event_time
            if etype in ("OUT", "ACCESS"):
                if bucket["last_out"] is None or event_time > bucket["last_out"]:
                    bucket["last_out"] = event_time
            if bucket["last_out"] is None or event_time > bucket["last_out"]:
                bucket["last_out"] = event_time
        for bucket in grouped.values():
            if bucket["first_in"] and bucket["last_out"] and bucket["last_out"] <= bucket["first_in"]:
                bucket["last_out"] = None
        return grouped

    # ------------------------------------------------------------ 시간 계산
    def compute_metrics(
        self,
        employee: Employees,
        work_date: date,
        check_in: Optional[datetime],
        check_out: Optional[datetime],
        day_type: str,
    ) -> Dict[str, Any]:
        """출퇴근 시각을 기준으로 근무/지각/연장/야간 시간을 계산한다."""
        std_start = parse_hhmm(employee.std_start, "09:00")
        std_end = parse_hhmm(employee.std_end, "18:00")
        break_minutes = employee.break_minutes if employee.break_minutes is not None else 60
        grace = employee.grace_minutes if employee.grace_minutes is not None else 0

        planned_in = datetime.combine(work_date, std_start)
        planned_out = datetime.combine(work_date, std_end)
        if planned_out <= planned_in:
            planned_out += timedelta(days=1)
        scheduled = max(int((planned_out - planned_in).total_seconds() // 60) - break_minutes, 0)

        metrics = {
            "scheduled_minutes": 0 if day_type != "weekday" else scheduled,
            "work_minutes": 0,
            "overtime_minutes": 0,
            "night_minutes": 0,
            "holiday_minutes": 0,
            "late_minutes": 0,
            "early_leave_minutes": 0,
        }
        if not check_in or not check_out:
            return metrics

        gross = int((check_out - check_in).total_seconds() // 60)
        if gross <= 0:
            return metrics
        worked = max(gross - (break_minutes if gross > 240 else 0), 0)
        metrics["work_minutes"] = worked
        metrics["night_minutes"] = night_minutes_between(check_in, check_out)

        if day_type in ("saturday", "sunday", "holiday"):
            metrics["holiday_minutes"] = worked
            metrics["overtime_minutes"] = 0
            return metrics

        late = int((check_in - planned_in).total_seconds() // 60)
        metrics["late_minutes"] = max(late - grace, 0) if late > 0 else 0
        early = int((planned_out - check_out).total_seconds() // 60)
        metrics["early_leave_minutes"] = max(early, 0)
        metrics["overtime_minutes"] = max(worked - scheduled, 0)
        return metrics

    def decide_status(self, metrics: Dict[str, Any], day_type: str, has_log: bool) -> str:
        """계산 결과로 근태 상태를 자동 판정한다."""
        if not has_log:
            return "absent"
        if day_type in ("saturday", "sunday", "holiday"):
            return "holiday_work"
        if metrics["late_minutes"] > 0 and metrics["early_leave_minutes"] > 0:
            return "late"
        if metrics["late_minutes"] > 0:
            return "late"
        if metrics["early_leave_minutes"] > 0:
            return "early_leave"
        return "normal"

    # ------------------------------------------------------------- 일일 정산
    async def settle_date(self, work_date: date, emp_nos: Optional[List[str]] = None) -> Dict[str, Any]:
        """지정 일자의 근태를 자동 정산한다. 확정(잠금)된 레코드는 건드리지 않는다."""
        employees = await self.load_employees(emp_nos)
        pairs = await self.extract_pairs(work_date)
        day_type = day_type_of(work_date)

        existing_stmt = select(Daily_attendances).where(Daily_attendances.work_date == work_date)
        existing_result = await self.db.execute(existing_stmt)
        existing = {row.emp_no: row for row in existing_result.scalars().all()}

        approved_leaves = await self._approved_leaves_on(work_date)
        approved_weekend = await self._approved_weekend_on(work_date)

        created, updated, skipped = 0, 0, 0
        for emp_no, employee in employees.items():
            record = existing.get(emp_no)
            if record is not None and (record.locked or record.confirm_status == "ceo_approved"):
                skipped += 1
                continue

            bucket = pairs.get(emp_no, {})
            raw_in = bucket.get("first_in")
            raw_out = bucket.get("last_out")
            log_count = bucket.get("count", 0)

            leave = approved_leaves.get(emp_no)
            weekend = approved_weekend.get(emp_no)

            if day_type == "weekday" and not raw_in and not leave:
                # 평일 무기록 → 결근 후보
                pass
            if day_type != "weekday" and not raw_in and not weekend:
                # 주말 무기록은 정산 대상에서 제외
                if record is None:
                    continue

            metrics = self.compute_metrics(employee, work_date, raw_in, raw_out, day_type)
            status = self.decide_status(metrics, day_type, bool(raw_in))
            reason_code = None
            reason_note = None

            if leave is not None:
                status = "leave"
                reason_code = {"annual": "ANNUAL", "sick": "SICK", "converted": "CONVERTED_OFF"}.get(
                    leave.leave_type, "ANNUAL"
                )
                reason_note = f"휴가 품의 #{leave.id} 승인 반영"
                metrics["scheduled_minutes"] = metrics["scheduled_minutes"] or 480
                metrics["late_minutes"] = 0
                metrics["early_leave_minutes"] = 0
            elif status == "absent":
                reason_code = "ABSENT"
                reason_note = "단말기 출입기록 없음"
            elif status == "holiday_work":
                reason_code = "HOLIDAY_WORK"
                reason_note = (
                    f"휴일근무 신청 #{weekend.id} 대조 완료" if weekend else "휴일 출입기록 감지 (사전신청 없음)"
                )
            elif status == "late":
                reason_code = "LATE_TRAFFIC"
                reason_note = f"지각 {metrics['late_minutes']}분 자동 판정"
            elif status == "early_leave":
                reason_code = "EARLY_LEAVE"
                reason_note = f"조기퇴근 {metrics['early_leave_minutes']}분 자동 판정"
            else:
                reason_code = "NORMAL"

            payload = {
                "emp_no": emp_no,
                "employee_name": employee.name,
                "department": employee.department,
                "work_date": work_date,
                "day_type": day_type,
                "raw_check_in": as_utc(raw_in),
                "raw_check_out": as_utc(raw_out),
                "log_count": log_count,
                "offset_minutes": (record.offset_minutes if record else 0) or 0,
                "status": status,
                "confirm_status": "draft",
                "locked": False,
                "leave_request_id": leave.id if leave else None,
                **metrics,
            }

            if record is None:
                payload["check_in"] = as_utc(raw_in)
                payload["check_out"] = as_utc(raw_out)
                payload["reason_code"] = reason_code
                payload["reason_note"] = reason_note
                payload["adjusted"] = False
                payload["adjust_history"] = "[]"
                self.db.add(Daily_attendances(**payload))
                created += 1
            else:
                # 수동 조정된 확정시각은 유지한다
                if not record.adjusted:
                    record.check_in = as_utc(raw_in)
                    record.check_out = as_utc(raw_out)
                    record.reason_code = reason_code
                    record.reason_note = reason_note
                for key, value in payload.items():
                    if key in ("check_in", "check_out", "reason_code", "reason_note", "adjusted", "adjust_history"):
                        continue
                    setattr(record, key, value)
                if record.adjusted and record.check_in:
                    manual = self.compute_metrics(
                        employee, work_date, to_naive(record.check_in), to_naive(record.check_out), day_type
                    )
                    for key, value in manual.items():
                        setattr(record, key, value)
                if record.confirm_status == "rejected":
                    record.confirm_status = "draft"
                updated += 1

        await self.db.commit()
        return {
            "work_date": work_date.isoformat(),
            "day_type": day_type,
            "created": created,
            "updated": updated,
            "locked_skipped": skipped,
            "employees_processed": len(employees),
            "logs_matched": sum(v.get("count", 0) for v in pairs.values()),
        }

    async def _approved_leaves_on(self, work_date: date) -> Dict[str, Leave_requests]:
        stmt = (
            select(Leave_requests)
            .where(Leave_requests.status == "approved")
            .where(Leave_requests.start_date <= work_date)
            .where(Leave_requests.end_date >= work_date)
        )
        result = await self.db.execute(stmt)
        return {row.emp_no: row for row in result.scalars().all()}

    async def _approved_weekend_on(self, work_date: date) -> Dict[str, Weekend_work_requests]:
        stmt = (
            select(Weekend_work_requests)
            .where(Weekend_work_requests.status == "approved")
            .where(Weekend_work_requests.work_date == work_date)
        )
        result = await self.db.execute(stmt)
        return {row.emp_no: row for row in result.scalars().all()}

    # ------------------------------------------------------- Extra 근무 상계
    async def overtime_balance(self, emp_no: str) -> int:
        """연장근무 적립 잔여 시간(분)을 계산한다."""
        result = await self.db.execute(
            select(Overtime_banks)
            .where(Overtime_banks.emp_no == emp_no)
            .where(Overtime_banks.status != "rejected")
        )
        return sum((row.minutes or 0) for row in result.scalars().all())

    async def earn_overtime(self, work_date: date) -> Dict[str, Any]:
        """최종승인된 근태의 연장/휴일 근무시간을 Extra 뱅크에 적립한다."""
        result = await self.db.execute(
            select(Daily_attendances)
            .where(Daily_attendances.work_date == work_date)
            .where(Daily_attendances.confirm_status == "ceo_approved")
        )
        records = result.scalars().all()

        existing = await self.db.execute(
            select(Overtime_banks)
            .where(Overtime_banks.txn_type == "earn")
            .where(Overtime_banks.source_date == work_date)
        )
        already = {row.emp_no for row in existing.scalars().all()}

        earned = 0
        for record in records:
            if record.emp_no in already:
                continue
            minutes = (record.overtime_minutes or 0) + (record.holiday_minutes or 0)
            if minutes <= 0:
                continue
            balance = await self.overtime_balance(record.emp_no)
            self.db.add(
                Overtime_banks(
                    emp_no=record.emp_no,
                    employee_name=record.employee_name,
                    department=record.department,
                    txn_type="earn",
                    txn_date=date.today(),
                    source_date=work_date,
                    minutes=minutes,
                    balance_after=balance + minutes,
                    status="approved",
                    note=f"{work_date.isoformat()} 연장/휴일 근무 적립",
                )
            )
            earned += 1
        await self.db.commit()
        return {"earned_records": earned, "work_date": work_date.isoformat()}

    async def offset_late(self, attendance_id: int, minutes: int, actor: str) -> Dict[str, Any]:
        """지각 급여삭감을 Extra 근무시간으로 상계 처리한다."""
        record = await self.db.get(Daily_attendances, attendance_id)
        if record is None:
            raise ValueError("근태 레코드를 찾을 수 없습니다.")
        if record.locked:
            raise ValueError("최종 승인되어 잠긴 근태는 상계할 수 없습니다.")
        remaining_late = (record.late_minutes or 0) - (record.offset_minutes or 0)
        if remaining_late <= 0:
            raise ValueError("상계 가능한 지각 시간이 없습니다.")
        balance = await self.overtime_balance(record.emp_no)
        use = min(minutes, remaining_late, balance)
        if use <= 0:
            raise ValueError(f"적립 잔여시간이 부족합니다. (잔여 {balance}분)")

        record.offset_minutes = (record.offset_minutes or 0) + use
        record.reason_note = f"{record.reason_note or ''} / Extra {use}분 상계".strip(" /")
        self.db.add(
            Overtime_banks(
                emp_no=record.emp_no,
                employee_name=record.employee_name,
                department=record.department,
                txn_type="offset_late",
                txn_date=date.today(),
                source_date=record.work_date,
                minutes=-use,
                balance_after=balance - use,
                target_attendance_id=record.id,
                status="approved",
                note=f"{actor} 처리 · 지각 {use}분 상계",
            )
        )
        await self.db.commit()
        return {
            "attendance_id": record.id,
            "offset_minutes": record.offset_minutes,
            "used_minutes": use,
            "balance_after": balance - use,
        }

    # ------------------------------------------------------------ 급여 집계
    async def calculate_payroll(
        self,
        run_name: str,
        pay_cycle: str,
        period_start: date,
        period_end: date,
        confirmed_only: bool = True,
    ) -> Dict[str, Any]:
        """지급주기별 근태 데이터를 집계하여 급여 항목을 계산한다."""
        employees = await self.load_employees()
        targets = {k: v for k, v in employees.items() if (v.pay_cycle or "monthly") == pay_cycle}
        if not targets:
            raise ValueError(f"{pay_cycle} 지급주기에 해당하는 직원이 없습니다.")

        stmt = (
            select(Daily_attendances)
            .where(Daily_attendances.work_date >= period_start)
            .where(Daily_attendances.work_date <= period_end)
        )
        result = await self.db.execute(stmt)
        records = [r for r in result.scalars().all() if r.emp_no in targets]
        if confirmed_only:
            records = [r for r in records if r.confirm_status == "ceo_approved"]

        reasons = await self.load_reasons()
        buckets: Dict[str, Dict[str, Any]] = {}
        for record in records:
            b = buckets.setdefault(
                record.emp_no,
                {
                    "regular_minutes": 0,
                    "overtime_minutes": 0,
                    "holiday_minutes": 0,
                    "night_minutes": 0,
                    "late_minutes": 0,
                    "offset_minutes": 0,
                    "absent_days": 0.0,
                    "leave_days": 0.0,
                    "work_days": 0,
                    "confirmed_days": 0,
                },
            )
            scheduled = record.scheduled_minutes or 0
            worked = record.work_minutes or 0
            overtime = record.overtime_minutes or 0
            holiday = record.holiday_minutes or 0
            b["regular_minutes"] += max(min(worked, scheduled) - holiday, 0) if scheduled else 0
            b["overtime_minutes"] += overtime
            b["holiday_minutes"] += holiday
            b["night_minutes"] += record.night_minutes or 0
            b["late_minutes"] += record.late_minutes or 0
            b["offset_minutes"] += record.offset_minutes or 0
            if record.status == "absent":
                b["absent_days"] += 1
            if record.status == "leave":
                b["leave_days"] += 1
            if worked > 0:
                b["work_days"] += 1
            if record.confirm_status == "ceo_approved":
                b["confirmed_days"] += 1

        from models.payroll_items import Payroll_items
        from models.payroll_runs import Payroll_runs

        run = Payroll_runs(
            run_name=run_name,
            pay_cycle=pay_cycle,
            period_start=period_start,
            period_end=period_end,
            status="calculated",
            employee_count=len(buckets),
            total_amount=0,
            confirmed_only=confirmed_only,
            calculated_at=as_utc(datetime.now()),
            note=f"{period_start.isoformat()} ~ {period_end.isoformat()} 확정근태 집계",
        )
        self.db.add(run)
        await self.db.commit()
        run_id = run.id

        holiday_rate = DEFAULT_HOLIDAY_PREMIUM
        total_amount = 0.0
        items_payload: List[Dict[str, Any]] = []

        for emp_no, b in buckets.items():
            employee = targets[emp_no]
            hourly = float(employee.hourly_rate or 0)
            if hourly <= 0:
                monthly = float(employee.monthly_salary or 0)
                hourly = round(monthly / 209, 2) if monthly else 0.0

            regular_hours = b["regular_minutes"] / 60
            overtime_hours = b["overtime_minutes"] / 60
            holiday_hours = b["holiday_minutes"] / 60
            night_hours = b["night_minutes"] / 60

            if (employee.pay_type or "hourly") == "monthly":
                divisor = {"weekly": 4.345, "biweekly": 2.172, "monthly": 1.0}.get(pay_cycle, 1.0)
                base_pay = round(float(employee.monthly_salary or 0) / divisor, 0)
            else:
                base_pay = round(regular_hours * hourly, 0)

            overtime_pay = round(overtime_hours * hourly * 1.5, 0)
            holiday_pay = round(holiday_hours * hourly * holiday_rate, 0)
            night_pay = round(night_hours * hourly * 0.5, 0)

            late_reason = reasons.get("LATE_TRAFFIC")
            deduct_rate = float(late_reason.deduct_rate) if late_reason and late_reason.deduct_rate is not None else 1.0
            gross_late = b["late_minutes"] / 60 * hourly * deduct_rate
            offset_credit = round(min(b["offset_minutes"], b["late_minutes"]) / 60 * hourly * deduct_rate, 0)
            late_deduction = round(max(gross_late - offset_credit, 0), 0)
            absent_deduction = round(b["absent_days"] * 8 * hourly, 0)

            gross_pay = base_pay + overtime_pay + holiday_pay + night_pay
            net_pay = round(gross_pay - late_deduction - absent_deduction, 0)
            total_amount += net_pay

            item = Payroll_items(
                payroll_run_id=run_id,
                emp_no=emp_no,
                employee_name=employee.name,
                department=employee.department,
                pay_cycle=pay_cycle,
                period_start=period_start,
                period_end=period_end,
                regular_minutes=b["regular_minutes"],
                overtime_minutes=b["overtime_minutes"],
                holiday_minutes=b["holiday_minutes"],
                night_minutes=b["night_minutes"],
                late_minutes=b["late_minutes"],
                offset_minutes=b["offset_minutes"],
                absent_days=b["absent_days"],
                leave_days=b["leave_days"],
                work_days=b["work_days"],
                confirmed_days=b["confirmed_days"],
                base_pay=base_pay,
                overtime_pay=overtime_pay,
                holiday_pay=holiday_pay,
                night_pay=night_pay,
                late_deduction=late_deduction,
                offset_credit=offset_credit,
                absent_deduction=absent_deduction,
                gross_pay=gross_pay,
                net_pay=net_pay,
            )
            self.db.add(item)
            items_payload.append(
                {
                    "emp_no": emp_no,
                    "employee_name": employee.name,
                    "department": employee.department,
                    "net_pay": net_pay,
                    "gross_pay": gross_pay,
                    "late_deduction": late_deduction,
                    "offset_credit": offset_credit,
                }
            )

        run_obj = await self.db.get(Payroll_runs, run_id)
        if run_obj is not None:
            run_obj.total_amount = round(total_amount, 0)
        await self.db.commit()

        return {
            "payroll_run_id": run_id,
            "run_name": run_name,
            "pay_cycle": pay_cycle,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "employee_count": len(buckets),
            "total_amount": round(total_amount, 0),
            "records_used": len(records),
            "items": items_payload,
        }

    # ------------------------------------------------------------- 대시보드
    async def dashboard(self, period_start: date, period_end: date) -> Dict[str, Any]:
        """팀별/직원별 근태 대시보드 집계를 생성한다."""
        stmt = (
            select(Daily_attendances)
            .where(Daily_attendances.work_date >= period_start)
            .where(Daily_attendances.work_date <= period_end)
        )
        result = await self.db.execute(stmt)
        records = result.scalars().all()

        summary = {
            "total_records": len(records),
            "normal": 0,
            "late": 0,
            "early_leave": 0,
            "absent": 0,
            "leave": 0,
            "holiday_work": 0,
            "overtime_minutes": 0,
            "holiday_minutes": 0,
            "late_minutes": 0,
            "offset_minutes": 0,
            "pending_approvals": 0,
            "confirmed": 0,
        }
        by_dept: Dict[str, Dict[str, Any]] = {}
        by_emp: Dict[str, Dict[str, Any]] = {}
        trend: Dict[str, Dict[str, Any]] = {}

        for r in records:
            status = r.status or "normal"
            if status in summary:
                summary[status] += 1
            summary["overtime_minutes"] += r.overtime_minutes or 0
            summary["holiday_minutes"] += r.holiday_minutes or 0
            summary["late_minutes"] += r.late_minutes or 0
            summary["offset_minutes"] += r.offset_minutes or 0
            if r.confirm_status == "ceo_approved":
                summary["confirmed"] += 1
            elif r.confirm_status in ("submitted", "manager_approved"):
                summary["pending_approvals"] += 1

            dept = r.department or "미지정"
            d = by_dept.setdefault(
                dept,
                {
                    "department": dept,
                    "records": 0,
                    "normal": 0,
                    "late": 0,
                    "absent": 0,
                    "leave": 0,
                    "holiday_work": 0,
                    "overtime_minutes": 0,
                    "late_minutes": 0,
                },
            )
            d["records"] += 1
            if status in d:
                d[status] += 1
            d["overtime_minutes"] += r.overtime_minutes or 0
            d["late_minutes"] += r.late_minutes or 0

            e = by_emp.setdefault(
                r.emp_no,
                {
                    "emp_no": r.emp_no,
                    "employee_name": r.employee_name,
                    "department": dept,
                    "records": 0,
                    "work_minutes": 0,
                    "overtime_minutes": 0,
                    "holiday_minutes": 0,
                    "late_count": 0,
                    "late_minutes": 0,
                    "offset_minutes": 0,
                    "absent_days": 0,
                    "leave_days": 0,
                },
            )
            e["records"] += 1
            e["work_minutes"] += r.work_minutes or 0
            e["overtime_minutes"] += r.overtime_minutes or 0
            e["holiday_minutes"] += r.holiday_minutes or 0
            e["offset_minutes"] += r.offset_minutes or 0
            if (r.late_minutes or 0) > 0:
                e["late_count"] += 1
                e["late_minutes"] += r.late_minutes or 0
            if status == "absent":
                e["absent_days"] += 1
            if status == "leave":
                e["leave_days"] += 1

            key = r.work_date.isoformat()
            t = trend.setdefault(key, {"date": key, "normal": 0, "late": 0, "absent": 0, "overtime_minutes": 0})
            if status in t:
                t[status] += 1
            t["overtime_minutes"] += r.overtime_minutes or 0

        for d in by_dept.values():
            d["attendance_rate"] = (
                round((d["normal"] + d["leave"] + d["holiday_work"]) / d["records"] * 100, 1) if d["records"] else 0
            )

        return {
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "summary": summary,
            "by_department": sorted(by_dept.values(), key=lambda x: -x["records"]),
            "by_employee": sorted(by_emp.values(), key=lambda x: -x["late_minutes"]),
            "trend": sorted(trend.values(), key=lambda x: x["date"]),
        }

    # ------------------------------------------------------ 조정 이력 유틸
    @staticmethod
    def append_history(raw: Optional[str], entry: Dict[str, Any]) -> str:
        try:
            history = json.loads(raw) if raw else []
            if not isinstance(history, list):
                history = []
        except (ValueError, TypeError):
            history = []
        history.append(entry)
        return json.dumps(history, ensure_ascii=False)