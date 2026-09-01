"""근태 집계/정산/전자결재/급여집계 커스텀 API."""

import json
import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from models.access_logs import Access_logs
from models.daily_attendances import Daily_attendances
from models.employees import Employees
from models.leave_balances import Leave_balances
from models.leave_requests import Leave_requests
from models.overtime_banks import Overtime_banks
from models.weekend_work_requests import Weekend_work_requests
from services.approval_flow import ApprovalFlowService
from services.attendance_engine import AttendanceEngine, as_utc, day_type_of, to_naive
from services.hikvision_sync import build_hikvision_client, sync_events

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/attendance", tags=["attendance"])


# --------------------------------------------------------------- 스키마
class ImportLogsRequest(BaseModel):
    records: List[Dict[str, Any]]
    terminal_id: Optional[str] = "HIK-MAIN-01"
    device_name: Optional[str] = "Hikvision 얼굴인식 단말기"
    source: Optional[str] = "upload"


class SettleRequest(BaseModel):
    work_date: date
    emp_nos: Optional[List[str]] = None


class AdjustRequest(BaseModel):
    attendance_id: int
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    reason_code: Optional[str] = None
    reason_note: Optional[str] = None
    actor_emp_no: str


class SubmitDailyCloseRequest(BaseModel):
    work_date: date
    requester_emp_no: str
    department: Optional[str] = None


class SubmitRequestDoc(BaseModel):
    doc_type: str
    entity_id: int
    requester_emp_no: str


class ApprovalActionRequest(BaseModel):
    approval_id: int
    actor_emp_no: str
    comment: Optional[str] = ""


class RejectRequest(BaseModel):
    approval_id: int
    actor_emp_no: str
    reason: str


class OffsetRequest(BaseModel):
    attendance_id: int
    minutes: int
    actor_emp_no: str


class ConvertRequest(BaseModel):
    emp_no: str
    minutes: int
    note: Optional[str] = ""


class PayrollRequest(BaseModel):
    run_name: Optional[str] = None
    pay_cycle: str
    period_start: date
    period_end: date
    confirmed_only: bool = True


class PeriodRequest(BaseModel):
    period_start: date
    period_end: date


class SeedRequest(BaseModel):
    days: int = 14


class HikvisionSyncRequest(BaseModel):
    start_time: datetime
    end_time: datetime
    page_size: int = 100


# --------------------------------------------------- 원시 출입기록 연동
@router.post("/import_logs")
async def import_logs(data: ImportLogsRequest, db: AsyncSession = Depends(get_db)):
    """Hikvision 단말기 출입기록을 취합 적재한다."""
    if not data.records:
        raise HTTPException(status_code=400, detail="적재할 출입기록이 없습니다.")

    result = await db.execute(select(Employees))
    employees = result.scalars().all()
    by_emp_no = {e.emp_no: e for e in employees}
    by_terminal = {e.terminal_user_id: e for e in employees if e.terminal_user_id}

    inserted, skipped = 0, 0
    for row in data.records:
        emp_no = str(row.get("emp_no") or row.get("employeeNo") or "").strip()
        terminal_user = str(row.get("terminal_user_id") or row.get("userId") or "").strip()
        employee = by_emp_no.get(emp_no) or by_terminal.get(terminal_user)
        if employee is None:
            skipped += 1
            continue
        raw_time = row.get("event_time") or row.get("time") or row.get("eventTime")
        event_time = to_naive(raw_time if isinstance(raw_time, datetime) else str(raw_time or ""))
        if event_time is None:
            skipped += 1
            continue
        db.add(
            Access_logs(
                emp_no=employee.emp_no,
                employee_name=employee.name,
                terminal_id=str(row.get("terminal_id") or data.terminal_id),
                device_name=str(row.get("device_name") or data.device_name),
                event_time=as_utc(event_time),
                event_date=event_time.date(),
                event_type=str(row.get("event_type") or row.get("direction") or "ACCESS").upper(),
                auth_mode=str(row.get("auth_mode") or "face"),
                source=data.source or "upload",
                raw_payload=json.dumps(row, ensure_ascii=False, default=str),
            )
        )
        inserted += 1
    await db.commit()
    return {"inserted": inserted, "skipped": skipped, "message": f"출입기록 {inserted}건 적재 완료"}


@router.post("/hikvision/sync")
async def sync_hikvision(data: HikvisionSyncRequest, db: AsyncSession = Depends(get_db)):
    """Hikvision ISAPI 이벤트를 읽어 신규 출입기록으로 저장한다."""
    if data.end_time <= data.start_time:
        raise HTTPException(status_code=400, detail="end_time debe ser posterior a start_time")

    try:
        client = build_hikvision_client(settings)
        return {**await sync_events(db, client, data.start_time, data.end_time, data.page_size), "source": "hikvision_isapi"}
    except (ConnectionError, ValueError) as exc:
        logger.error("Hikvision sync failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/reset_demo")
async def reset_demo(db: AsyncSession = Depends(get_db)):
    """데모/검증용 트랜잭션 데이터를 초기화한다(마스터 데이터는 유지)."""
    from models.approvals import Approvals
    from models.payroll_items import Payroll_items
    from models.payroll_runs import Payroll_runs

    removed: Dict[str, int] = {}
    for label, model in (
        ("payroll_items", Payroll_items),
        ("payroll_runs", Payroll_runs),
        ("overtime_banks", Overtime_banks),
        ("approvals", Approvals),
        ("daily_attendances", Daily_attendances),
        ("access_logs", Access_logs),
    ):
        result = await db.execute(delete(model))
        removed[label] = int(result.rowcount or 0)
    await db.commit()
    return {"removed": removed, "message": "트랜잭션 데이터 초기화 완료"}


@router.post("/seed_demo_logs")
async def seed_demo_logs(data: SeedRequest, db: AsyncSession = Depends(get_db)):
    """데모용 단말기 출입기록을 생성한다(기존 기록이 없을 때만)."""
    existing = await db.execute(select(Access_logs).limit(1))
    if existing.scalars().first() is not None:
        return {"inserted": 0, "message": "이미 출입기록이 존재합니다."}

    result = await db.execute(select(Employees))
    employees = [e for e in result.scalars().all() if e.active is not False]
    if not employees:
        raise HTTPException(status_code=400, detail="직원 마스터가 없습니다.")

    today = date.today()
    patterns = {
        "E001": [(0, 0), (0, 0)],
        "E002": [(2, -5), (0, 20)],
        "E003": [(-10, 0), (0, 45)],
        "E004": [(18, 0), (0, 95)],
        "E005": [(0, 0), (-35, 0)],
        "E006": [(25, 0), (0, 60)],
        "E007": [(-5, 0), (0, 30)],
        "E008": [(12, 0), (0, 130)],
    }
    inserted = 0
    for offset in range(data.days, 0, -1):
        work_date = today - timedelta(days=offset)
        dtype = day_type_of(work_date)
        for emp in employees:
            if dtype != "weekday":
                # 주말은 생산팀 일부만 근무
                if emp.department != "생산팀" or offset % 7 != 1:
                    continue
            if dtype == "weekday" and emp.emp_no == "E005" and offset in (3, 9):
                continue  # 결근/휴가 케이스
            late_min, extra_min = patterns.get(emp.emp_no, [(0, 0), (0, 0)])[0], patterns.get(
                emp.emp_no, [(0, 0), (0, 0)]
            )[1]
            base_h, base_m = [int(x) for x in (emp.std_start or "09:00").split(":")]
            end_h, end_m = [int(x) for x in (emp.std_end or "18:00").split(":")]
            jitter = (offset * 7 + len(emp.emp_no)) % 9
            in_time = datetime.combine(work_date, datetime.min.time()).replace(hour=base_h, minute=base_m) + timedelta(
                minutes=late_min[0] + jitter - 4
            )
            out_time = datetime.combine(work_date, datetime.min.time()).replace(hour=end_h, minute=end_m) + timedelta(
                minutes=extra_min[1] + (jitter * 3 if dtype == "weekday" else 0)
            )
            if dtype != "weekday":
                in_time = datetime.combine(work_date, datetime.min.time()).replace(hour=9)
                out_time = datetime.combine(work_date, datetime.min.time()).replace(hour=14)

            events = [(in_time, "IN"), (in_time + timedelta(hours=3, minutes=10), "ACCESS"), (out_time, "OUT")]
            for event_time, event_type in events:
                db.add(
                    Access_logs(
                        emp_no=emp.emp_no,
                        employee_name=emp.name,
                        terminal_id="HIK-MAIN-01",
                        device_name="Hikvision DS-K1T671 얼굴인식 단말기",
                        event_time=as_utc(event_time),
                        event_date=event_time.date(),
                        event_type=event_type,
                        auth_mode="face",
                        source="api",
                        raw_payload=json.dumps(
                            {"employeeNo": emp.terminal_user_id, "verifyMode": "face"}, ensure_ascii=False
                        ),
                    )
                )
                inserted += 1
    await db.commit()
    return {"inserted": inserted, "message": f"데모 출입기록 {inserted}건 생성"}


# ------------------------------------------------------------ 근태 정산
@router.post("/settle")
async def settle(data: SettleRequest, db: AsyncSession = Depends(get_db)):
    """지정 일자의 출퇴근을 자동 추출하고 근태를 정산한다."""
    engine = AttendanceEngine(db)
    try:
        return await engine.settle_date(data.work_date, data.emp_nos)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.error(f"근태 정산 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"근태 정산 실패: {e}")


@router.post("/settle_range")
async def settle_range(data: PeriodRequest, db: AsyncSession = Depends(get_db)):
    """기간 전체 근태를 일괄 정산한다."""
    if data.period_end < data.period_start:
        raise HTTPException(status_code=400, detail="종료일이 시작일보다 앞설 수 없습니다.")
    engine = AttendanceEngine(db)
    results, cursor = [], data.period_start
    try:
        while cursor <= data.period_end:
            results.append(await engine.settle_date(cursor))
            cursor += timedelta(days=1)
    except Exception as e:  # noqa: BLE001
        logger.error(f"기간 정산 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"기간 정산 실패: {e}")
    return {
        "days": len(results),
        "created": sum(r["created"] for r in results),
        "updated": sum(r["updated"] for r in results),
        "locked_skipped": sum(r["locked_skipped"] for r in results),
        "details": results,
    }


@router.post("/adjust")
async def adjust(data: AdjustRequest, db: AsyncSession = Depends(get_db)):
    """근태담당자가 출퇴근 시각 및 사유를 조정한다(이력 기록)."""
    record = await db.get(Daily_attendances, data.attendance_id)
    if record is None:
        raise HTTPException(status_code=404, detail="근태 레코드를 찾을 수 없습니다.")
    if record.locked:
        raise HTTPException(status_code=400, detail="CEO 최종승인으로 잠긴 근태는 조정할 수 없습니다.")

    engine = AttendanceEngine(db)
    before = {
        "check_in": record.check_in.isoformat() if record.check_in else None,
        "check_out": record.check_out.isoformat() if record.check_out else None,
        "reason_code": record.reason_code,
        "status": record.status,
    }
    if data.check_in is not None:
        record.check_in = to_naive(data.check_in)
    if data.check_out is not None:
        record.check_out = to_naive(data.check_out)
    if data.reason_code is not None:
        record.reason_code = data.reason_code
    if data.reason_note is not None:
        record.reason_note = data.reason_note

    result = await db.execute(select(Employees).where(Employees.emp_no == record.emp_no))
    employee = result.scalars().first()
    if employee is not None and record.check_in:
        metrics = engine.compute_metrics(
            employee,
            record.work_date,
            to_naive(record.check_in),
            to_naive(record.check_out),
            record.day_type or day_type_of(record.work_date),
        )
        for key, value in metrics.items():
            setattr(record, key, value)
        if record.status not in ("leave", "holiday_work", "business_trip"):
            record.status = engine.decide_status(metrics, record.day_type or "weekday", True)

    record.adjusted = True
    record.adjusted_by = data.actor_emp_no
    record.adjust_history = AttendanceEngine.append_history(
        record.adjust_history,
        {
            "at": datetime.now().isoformat(timespec="seconds"),
            "by": data.actor_emp_no,
            "before": before,
            "after": {
                "check_in": record.check_in.isoformat() if record.check_in else None,
                "check_out": record.check_out.isoformat() if record.check_out else None,
                "reason_code": record.reason_code,
                "status": record.status,
            },
        },
    )
    if record.confirm_status in ("rejected", "submitted", "manager_approved"):
        record.confirm_status = "draft"
    await db.commit()
    return {
        "attendance_id": record.id,
        "status": record.status,
        "work_minutes": record.work_minutes,
        "late_minutes": record.late_minutes,
        "overtime_minutes": record.overtime_minutes,
        "message": "근태 조정 완료 (이력 기록됨)",
    }


# -------------------------------------------------------------- 전자결재
@router.post("/approval/submit_daily_close")
async def submit_daily_close(data: SubmitDailyCloseRequest, db: AsyncSession = Depends(get_db)):
    """일일 근태 마감 결재를 상신한다."""
    flow = ApprovalFlowService(db)
    try:
        return await flow.submit_daily_close(data.work_date, data.requester_emp_no, data.department)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.error(f"마감 상신 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"마감 상신 실패: {e}")


@router.post("/approval/submit_request")
async def submit_request(data: SubmitRequestDoc, db: AsyncSession = Depends(get_db)):
    """휴가품의/휴일근무/연장전환 문서를 결재 상신한다."""
    flow = ApprovalFlowService(db)
    try:
        return await flow.submit_request(data.doc_type, data.entity_id, data.requester_emp_no)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.error(f"결재 상신 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"결재 상신 실패: {e}")


@router.post("/approval/approve")
async def approve(data: ApprovalActionRequest, db: AsyncSession = Depends(get_db)):
    """현재 결재 단계를 승인한다."""
    flow = ApprovalFlowService(db)
    try:
        return await flow.approve(data.approval_id, data.actor_emp_no, data.comment or "")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.error(f"결재 승인 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"결재 승인 실패: {e}")


@router.post("/approval/reject")
async def reject(data: RejectRequest, db: AsyncSession = Depends(get_db)):
    """결재를 반려한다."""
    flow = ApprovalFlowService(db)
    try:
        return await flow.reject(data.approval_id, data.actor_emp_no, data.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.error(f"결재 반려 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"결재 반려 실패: {e}")


# ------------------------------------------------- 휴가/연장근무 전환/상계
@router.post("/leave/apply")
async def leave_apply(data: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    """휴가 품의를 등록하고 잔여를 예약(pending) 처리한다."""
    emp_no = str(data.get("emp_no") or "").strip()
    leave_type = str(data.get("leave_type") or "annual")
    if not emp_no:
        raise HTTPException(status_code=400, detail="사번이 필요합니다.")
    try:
        start = date.fromisoformat(str(data.get("start_date")))
        end = date.fromisoformat(str(data.get("end_date")))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="휴가 기간을 올바르게 입력하세요.")
    if end < start:
        raise HTTPException(status_code=400, detail="종료일이 시작일보다 앞설 수 없습니다.")

    result = await db.execute(select(Employees).where(Employees.emp_no == emp_no))
    employee = result.scalars().first()
    if employee is None:
        raise HTTPException(status_code=404, detail="직원을 찾을 수 없습니다.")

    half = str(data.get("half_day_type") or "full")
    days = 0.5 if half in ("am", "pm") else float((end - start).days + 1)

    result = await db.execute(
        select(Leave_balances)
        .where(Leave_balances.emp_no == emp_no)
        .where(Leave_balances.year == start.year)
        .where(Leave_balances.leave_type == leave_type)
    )
    balance = result.scalars().first()
    remaining = (
        float(balance.granted_days or 0) - float(balance.used_days or 0) - float(balance.pending_days or 0)
        if balance
        else 0.0
    )
    if balance is None or remaining < days:
        raise HTTPException(status_code=400, detail=f"휴가 잔여일수가 부족합니다. (잔여 {remaining}일 / 신청 {days}일)")

    entity = Leave_requests(
        emp_no=emp_no,
        employee_name=employee.name,
        department=employee.department,
        leave_type=leave_type,
        start_date=start,
        end_date=end,
        days=days,
        half_day_type=half,
        reason=str(data.get("reason") or ""),
        status="draft",
        reflected=False,
        reflected_count=0,
    )
    db.add(entity)
    balance.pending_days = float(balance.pending_days or 0) + days
    await db.commit()
    entity_id = entity.id

    flow = ApprovalFlowService(db)
    submitted = await flow.submit_request("leave_request", entity_id, emp_no)
    return {"leave_request_id": entity_id, "days": days, **submitted}


@router.post("/weekend/apply")
async def weekend_apply(data: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    """토/일 및 휴일 근무 신청을 등록하고 결재 상신한다."""
    emp_no = str(data.get("emp_no") or "").strip()
    if not emp_no:
        raise HTTPException(status_code=400, detail="사번이 필요합니다.")
    try:
        work_date = date.fromisoformat(str(data.get("work_date")))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="근무일을 올바르게 입력하세요.")

    result = await db.execute(select(Employees).where(Employees.emp_no == emp_no))
    employee = result.scalars().first()
    if employee is None:
        raise HTTPException(status_code=404, detail="직원을 찾을 수 없습니다.")

    dtype = data.get("day_type") or day_type_of(work_date)
    if dtype == "weekday":
        raise HTTPException(status_code=400, detail="평일은 휴일근무 신청 대상이 아닙니다.")

    planned_start = str(data.get("planned_start") or "09:00")
    planned_end = str(data.get("planned_end") or "14:00")
    try:
        sh, sm = [int(x) for x in planned_start.split(":")]
        eh, em = [int(x) for x in planned_end.split(":")]
    except ValueError:
        raise HTTPException(status_code=400, detail="근무 시간 형식이 올바르지 않습니다. (HH:MM)")
    planned_minutes = max((eh * 60 + em) - (sh * 60 + sm), 0)

    entity = Weekend_work_requests(
        emp_no=emp_no,
        employee_name=employee.name,
        department=employee.department,
        work_date=work_date,
        day_type=dtype,
        planned_start=planned_start,
        planned_end=planned_end,
        planned_minutes=planned_minutes,
        premium_rate=float(data.get("premium_rate") or 1.5),
        reason=str(data.get("reason") or ""),
        status="draft",
        matched=False,
    )
    db.add(entity)
    await db.commit()
    entity_id = entity.id

    flow = ApprovalFlowService(db)
    submitted = await flow.submit_request("weekend_work", entity_id, emp_no)
    return {"weekend_request_id": entity_id, "planned_minutes": planned_minutes, **submitted}


@router.post("/overtime/earn")
async def overtime_earn(data: SettleRequest, db: AsyncSession = Depends(get_db)):
    """확정된 근태의 연장/휴일 근무시간을 Extra 뱅크에 적립한다."""
    engine = AttendanceEngine(db)
    try:
        return await engine.earn_overtime(data.work_date)
    except Exception as e:  # noqa: BLE001
        logger.error(f"연장근무 적립 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"연장근무 적립 실패: {e}")


@router.post("/overtime/convert")
async def overtime_convert(data: ConvertRequest, db: AsyncSession = Depends(get_db)):
    """적립된 Extra 근무시간을 휴가로 전환 신청한다(결재 필요)."""
    engine = AttendanceEngine(db)
    balance = await engine.overtime_balance(data.emp_no)
    if data.minutes <= 0:
        raise HTTPException(status_code=400, detail="전환할 시간을 입력하세요.")
    if data.minutes > balance:
        raise HTTPException(status_code=400, detail=f"적립 잔여시간이 부족합니다. (잔여 {balance}분)")

    result = await db.execute(select(Employees).where(Employees.emp_no == data.emp_no))
    employee = result.scalars().first()
    if employee is None:
        raise HTTPException(status_code=404, detail="직원을 찾을 수 없습니다.")

    days = round(data.minutes / 480, 2)
    entity = Overtime_banks(
        emp_no=data.emp_no,
        employee_name=employee.name,
        department=employee.department,
        txn_type="convert_leave",
        txn_date=date.today(),
        minutes=-data.minutes,
        balance_after=balance - data.minutes,
        target_leave_days=days,
        status="draft",
        note=data.note or f"연장근무 {data.minutes}분 휴가 전환 신청",
    )
    db.add(entity)
    await db.commit()
    entity_id = entity.id

    flow = ApprovalFlowService(db)
    submitted = await flow.submit_request("overtime_convert", entity_id, data.emp_no)
    return {"overtime_bank_id": entity_id, "converted_days": days, "balance_before": balance, **submitted}


@router.post("/overtime/offset_late")
async def offset_late(data: OffsetRequest, db: AsyncSession = Depends(get_db)):
    """지각 급여삭감을 Extra 근무시간으로 상계한다."""
    engine = AttendanceEngine(db)
    try:
        return await engine.offset_late(data.attendance_id, data.minutes, data.actor_emp_no)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.error(f"지각 상계 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"지각 상계 실패: {e}")


@router.get("/overtime/balance")
async def overtime_balance(emp_no: str, db: AsyncSession = Depends(get_db)):
    """직원별 Extra 근무 적립 잔여시간을 조회한다."""
    engine = AttendanceEngine(db)
    minutes = await engine.overtime_balance(emp_no)
    return {"emp_no": emp_no, "balance_minutes": minutes, "convertible_days": round(minutes / 480, 2)}


# ------------------------------------------------------- 급여집계/대시보드
@router.post("/payroll/calculate")
async def payroll_calculate(data: PayrollRequest, db: AsyncSession = Depends(get_db)):
    """지급주기별 급여를 집계한다."""
    if data.period_end < data.period_start:
        raise HTTPException(status_code=400, detail="종료일이 시작일보다 앞설 수 없습니다.")
    engine = AttendanceEngine(db)
    label = {"weekly": "주급", "biweekly": "2주급", "monthly": "월급"}.get(data.pay_cycle, data.pay_cycle)
    run_name = data.run_name or f"{label} {data.period_start.isoformat()}~{data.period_end.isoformat()}"
    try:
        return await engine.calculate_payroll(
            run_name, data.pay_cycle, data.period_start, data.period_end, data.confirmed_only
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        logger.error(f"급여 집계 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"급여 집계 실패: {e}")


@router.post("/dashboard")
async def dashboard(data: PeriodRequest, db: AsyncSession = Depends(get_db)):
    """팀별/직원별 근태 대시보드 데이터를 반환한다."""
    engine = AttendanceEngine(db)
    try:
        return await engine.dashboard(data.period_start, data.period_end)
    except Exception as e:  # noqa: BLE001
        logger.error(f"대시보드 집계 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"대시보드 집계 실패: {e}")