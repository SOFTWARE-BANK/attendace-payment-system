"""Sincronizacion compartida de eventos Hikvision con la base local."""

import asyncio
import logging
import os
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.access_logs import Access_logs
from models.employees import Employees
from services.attendance_engine import as_utc, to_naive
from services.hikvision import HikvisionClient

logger = logging.getLogger(__name__)


def _auto_provision_enabled() -> bool:
    """HIKVISION_AUTO_PROVISION=true crea empleados al detectar IDs nuevos."""
    return str(os.getenv("HIKVISION_AUTO_PROVISION", "true")).strip().lower() in ("1", "true", "yes", "on")


async def _next_emp_no(db: AsyncSession) -> str:
    """Devuelve el siguiente emp_no libre del patron E###."""
    result = await db.execute(select(Employees.emp_no))
    highest = 0
    for (emp_no,) in result.all():
        match = re.fullmatch(r"E(\d+)", str(emp_no or "").strip())
        if match:
            highest = max(highest, int(match.group(1)))
    return f"E{highest + 1:03d}"


async def ensure_employee(
    db: AsyncSession,
    client: Any,
    employee_id: str,
    by_terminal_id: Dict[str, Employees],
) -> Optional[Employees]:
    """Devuelve el empleado asociado a un ID del terminal.

    Si el ID no existe y el auto-registro esta activo (HIKVISION_AUTO_PROVISION),
    consulta el directorio del lector (UserInfo/Search) y crea el empleado con
    los datos del dispositivo. No hace commit: se persiste junto con las
    checadas del mismo sync (atomico).
    """
    employee_id = str(employee_id or "").strip()
    if not employee_id:
        return None
    if employee_id in by_terminal_id:
        return by_terminal_id[employee_id]
    if not _auto_provision_enabled():
        return None
    user_info = await client.get_user_info(employee_id)
    if not user_info:
        return None
    name = str(user_info.get("name") or "").strip() or f"Usuario {employee_id}"
    employee = Employees(
        emp_no=await _next_emp_no(db),
        name=name,
        department="General",
        position=None,
        role="employee",
        email=None,
        pay_type="monthly",
        hourly_rate=0.0,
        monthly_salary=0.0,
        pay_cycle="monthly",
        std_start="09:00",
        std_end="18:00",
        break_minutes=60,
        grace_minutes=10,
        hire_date=date.today(),
        annual_leave_days=15.0,
        terminal_user_id=employee_id,
        manager_emp_no=None,
        active=True,
    )
    db.add(employee)
    await db.flush()
    logger.info(
        "Hikvision auto-provisioning: empleado %s (%s) creado con terminal_user_id=%s",
        employee.emp_no,
        name,
        employee_id,
    )
    return employee


async def sync_events(
    db: AsyncSession,
    client: HikvisionClient,
    start_time: datetime,
    end_time: datetime,
    page_size: int = 100,
) -> Dict[str, Any]:
    """Importa eventos del dispositivo evitando duplicados y usuarios sin mapear."""
    remote_events = await client.fetch_events(start_time, end_time, page_size)
    result = await db.execute(
        select(Access_logs).where(
            Access_logs.event_time >= to_naive(start_time),
            Access_logs.event_time < to_naive(end_time),
        )
    )
    existing_keys = {
        (row.emp_no, row.event_time.replace(tzinfo=None, microsecond=0) if row.event_time else None, row.event_type or "ACCESS", row.terminal_id or "")
        for row in result.scalars().all()
    }
    employee_result = await db.execute(select(Employees))
    employees = employee_result.scalars().all()
    by_emp_no = {employee.emp_no: employee for employee in employees}
    by_terminal_id = {employee.terminal_user_id: employee for employee in employees if employee.terminal_user_id}

    inserted = skipped = duplicates = 0
    unmatched_ids = set()
    provisioned: List[str] = []
    for event in remote_events:
        event_time = to_naive(event.get("event_time"))
        employee_id = str(event.get("employeeNo") or "").strip()
        employee = by_emp_no.get(employee_id) or by_terminal_id.get(employee_id)
        if employee is None and employee_id:
            employee = await ensure_employee(db, client, employee_id, by_terminal_id)
            if employee is not None:
                by_terminal_id[employee_id] = employee
                provisioned.append(employee_id)
        if employee is None or event_time is None:
            if employee_id and employee_id not in provisioned:
                unmatched_ids.add(employee_id)
            skipped += 1
            continue
        terminal_id = str(event.get("terminal_id") or client.base_url)
        event_type = str(event.get("event_type") or "ACCESS").upper()
        # Normalizar event_time a segundos para evitar problemas de precisión
        normalized_time = event_time.replace(microsecond=0) if event_time else event_time
        key = (employee.emp_no, normalized_time, event_type, terminal_id)
        if key in existing_keys:
            duplicates += 1
            logger.debug("Hikvision: duplicado detectado - key=%s", key)
            continue
        logger.debug("Hikvision: nuevo evento - key=%s, existing_keys count=%d", key, len(existing_keys))
        db.add(
            Access_logs(
                emp_no=employee.emp_no,
                employee_name=employee.name,
                terminal_id=terminal_id,
                device_name=event.get("device_name") or "Hikvision",
                event_time=event_time,
                event_date=event_time.date(),
                event_type=event_type,
                auth_mode=event.get("auth_mode") or "face",
                source="hikvision_isapi",
                raw_payload=event.get("raw_payload"),
            )
        )
        existing_keys.add(key)
        inserted += 1
    await db.commit()
    return {
        "fetched": len(remote_events),
        "inserted": inserted,
        "duplicates": duplicates,
        "skipped": skipped,
        "provisioned": provisioned,
        "unmatched_employee_ids": sorted(unmatched_ids)[:20],
    }


def build_hikvision_client(settings: Any) -> HikvisionClient:
    """Construye el cliente desde variables de entorno sin registrar secretos."""
    host = str(getattr(settings, "hikvision_host", "") or "").strip()
    username = str(getattr(settings, "hikvision_username", "") or "").strip()
    password = str(getattr(settings, "hikvision_password", "") or "")
    if not host or not username or not password:
        raise ValueError("Faltan HIKVISION_HOST, HIKVISION_USERNAME o HIKVISION_PASSWORD")

    def env_bool(name: str, default: bool = False) -> bool:
        return str(getattr(settings, name, default) or default).lower() in ("1", "true", "yes", "on")

    return HikvisionClient(
        host=host,
        username=username,
        password=password,
        port=int(getattr(settings, "hikvision_port", 80) or 80),
        use_https=env_bool("hikvision_use_https"),
        verify_ssl=env_bool("hikvision_verify_ssl"),
    )


async def background_sync_loop(stop_event: Any, interval_seconds: int = 60) -> None:
    """Sincroniza una ventana solapada periodicamente para no perder eventos."""
    from core.database import db_manager
    from core.config import settings

    while not stop_event.is_set():
        try:
            client = build_hikvision_client(settings)
            now = datetime.now(timezone.utc)
            async with db_manager.async_session_maker() as db:
                result = await sync_events(db, client, now - timedelta(seconds=interval_seconds * 2), now, 100)
            logger.info(
                "Hikvision background sync: fetched=%s inserted=%s duplicates=%s skipped=%s",
                result["fetched"], result["inserted"], result["duplicates"], result["skipped"],
            )
        except Exception as exc:
            logger.warning("Hikvision background sync failed: %s", exc)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        except asyncio.TimeoutError:
            continue
