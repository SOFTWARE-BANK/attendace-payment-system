import { createClient } from '@metagptx/web-sdk';

export const client = createClient();

/** 근태 시스템 커스텀 API 호출 래퍼 */
export async function callApi<T = unknown>(
  url: string,
  method: 'GET' | 'POST' | 'PUT' | 'DELETE',
  data: Record<string, unknown> = {},
): Promise<T> {
  const response = await client.apiCall.invoke({ url, method, data });
  return response.data as T;
}

/** FastAPI 검증 오류(detail 배열/객체)까지 안전하게 문자열로 변환한다. */
function stringifyDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') return item;
        const row = item as { loc?: unknown[]; msg?: string };
        const field = Array.isArray(row?.loc) ? row.loc.filter((p) => p !== 'body').join('.') : '';
        return [field, row?.msg].filter(Boolean).join(': ');
      })
      .filter(Boolean)
      .join(' / ');
  }
  if (detail && typeof detail === 'object') {
    const row = detail as { msg?: string; message?: string };
    return row.msg ?? row.message ?? '';
  }
  return '';
}

export function apiError(e: unknown, fallback = 'Request failed.'): string {
  const err = e as {
    data?: { detail?: unknown };
    response?: { data?: { detail?: unknown } };
    message?: string;
  };
  const detail =
    stringifyDetail(err?.data?.detail) || stringifyDetail(err?.response?.data?.detail);
  if (detail) return detail;
  return typeof err?.message === 'string' && err.message ? err.message : fallback;
}

/* ------------------------------------------------------------ 도메인 타입 */
export interface Employee {
  id: number;
  emp_no: string;
  name: string;
  department: string;
  position?: string;
  role?: string;
  pay_type?: string;
  hourly_rate?: number;
  monthly_salary?: number;
  pay_cycle?: string;
  std_start?: string;
  std_end?: string;
  break_minutes?: number;
  grace_minutes?: number;
  annual_leave_days?: number;
  terminal_user_id?: string;
  manager_emp_no?: string;
  active?: boolean;
}

export interface AccessLog {
  id: number;
  emp_no: string;
  employee_name?: string;
  terminal_id?: string;
  device_name?: string;
  event_time: string;
  event_date?: string;
  event_type?: string;
  auth_mode?: string;
  source?: string;
}

export interface DailyAttendance {
  id: number;
  emp_no: string;
  employee_name?: string;
  department?: string;
  work_date: string;
  day_type?: string;
  raw_check_in?: string | null;
  raw_check_out?: string | null;
  check_in?: string | null;
  check_out?: string | null;
  log_count?: number;
  scheduled_minutes?: number;
  work_minutes?: number;
  overtime_minutes?: number;
  night_minutes?: number;
  holiday_minutes?: number;
  late_minutes?: number;
  early_leave_minutes?: number;
  offset_minutes?: number;
  status?: string;
  reason_code?: string;
  reason_note?: string;
  adjusted?: boolean;
  adjusted_by?: string;
  adjust_history?: string;
  confirm_status?: string;
  approval_id?: number;
  locked?: boolean;
}

export interface AttendanceReason {
  id: number;
  code: string;
  name: string;
  category?: string;
  pay_effect?: string;
  deduct_rate?: number;
  requires_approval?: boolean;
  offsettable?: boolean;
  sort_order?: number;
  description?: string;
  active?: boolean;
}

export interface Approval {
  id: number;
  doc_no?: string;
  doc_type: string;
  title: string;
  target_date?: string;
  period_start?: string;
  period_end?: string;
  emp_no?: string;
  department?: string;
  requester_name?: string;
  current_step?: string;
  status?: string;
  hr_approver?: string;
  hr_approved_at?: string;
  hr_comment?: string;
  manager_approver?: string;
  manager_approved_at?: string;
  manager_comment?: string;
  ceo_approver?: string;
  ceo_approved_at?: string;
  ceo_comment?: string;
  rejected_by?: string;
  reject_reason?: string;
  record_count?: number;
  summary?: string;
}

export interface LeaveBalance {
  id: number;
  emp_no: string;
  employee_name?: string;
  department?: string;
  year: number;
  leave_type: string;
  granted_days?: number;
  used_days?: number;
  pending_days?: number;
  converted_days?: number;
  note?: string;
}

export interface LeaveRequest {
  id: number;
  emp_no: string;
  employee_name?: string;
  department?: string;
  leave_type: string;
  start_date: string;
  end_date: string;
  days?: number;
  half_day_type?: string;
  reason?: string;
  status?: string;
  approval_id?: number;
  reflected?: boolean;
  reflected_count?: number;
}

export interface WeekendWorkRequest {
  id: number;
  emp_no: string;
  employee_name?: string;
  department?: string;
  work_date: string;
  day_type?: string;
  planned_start?: string;
  planned_end?: string;
  planned_minutes?: number;
  actual_minutes?: number;
  premium_rate?: number;
  reason?: string;
  status?: string;
  approval_id?: number;
  matched?: boolean;
}

export interface OvertimeBank {
  id: number;
  emp_no: string;
  employee_name?: string;
  department?: string;
  txn_type: string;
  txn_date?: string;
  source_date?: string;
  minutes: number;
  balance_after?: number;
  target_leave_days?: number;
  target_attendance_id?: number;
  status?: string;
  note?: string;
}

export interface PayrollRun {
  id: number;
  run_name: string;
  pay_cycle: string;
  period_start: string;
  period_end: string;
  status?: string;
  employee_count?: number;
  total_amount?: number;
  confirmed_only?: boolean;
  calculated_at?: string;
  note?: string;
}

export interface PayrollItem {
  id: number;
  payroll_run_id: number;
  emp_no: string;
  employee_name?: string;
  department?: string;
  pay_cycle?: string;
  regular_minutes?: number;
  overtime_minutes?: number;
  holiday_minutes?: number;
  night_minutes?: number;
  late_minutes?: number;
  offset_minutes?: number;
  absent_days?: number;
  leave_days?: number;
  work_days?: number;
  confirmed_days?: number;
  base_pay?: number;
  overtime_pay?: number;
  holiday_pay?: number;
  night_pay?: number;
  late_deduction?: number;
  offset_credit?: number;
  absent_deduction?: number;
  gross_pay?: number;
  net_pay?: number;
}

export interface DashboardData {
  period_start: string;
  period_end: string;
  summary: {
    total_records: number;
    normal: number;
    late: number;
    early_leave: number;
    absent: number;
    leave: number;
    holiday_work: number;
    overtime_minutes: number;
    holiday_minutes: number;
    late_minutes: number;
    offset_minutes: number;
    pending_approvals: number;
    confirmed: number;
  };
  by_department: Array<{
    department: string;
    records: number;
    normal: number;
    late: number;
    absent: number;
    leave: number;
    holiday_work: number;
    overtime_minutes: number;
    late_minutes: number;
    attendance_rate: number;
  }>;
  by_employee: Array<{
    emp_no: string;
    employee_name?: string;
    department?: string;
    records: number;
    work_minutes: number;
    overtime_minutes: number;
    holiday_minutes: number;
    late_count: number;
    late_minutes: number;
    offset_minutes: number;
    absent_days: number;
    leave_days: number;
  }>;
  trend: Array<{ date: string; normal: number; late: number; absent: number; overtime_minutes: number }>;
}

/* ---------------------------------------------------------- 엔티티 조회 */
type EntityQuery = {
  query?: Record<string, unknown>;
  sort?: string;
  limit?: number;
  skip?: number;
};

/* eslint-disable @typescript-eslint/no-explicit-any */
export async function queryAll<T>(entity: string, options: EntityQuery = {}): Promise<T[]> {
  const store = (client.entities as any)[entity];
  const response = await store.query({
    query: options.query ?? {},
    sort: options.sort,
    limit: options.limit ?? 500,
    skip: options.skip ?? 0,
  });
  return (response?.data?.items ?? []) as T[];
}

export async function createEntity<T>(entity: string, data: Record<string, unknown>): Promise<T> {
  const store = (client.entities as any)[entity];
  const response = await store.create({ data });
  return response.data as T;
}

export async function updateEntity<T>(entity: string, id: number, data: Record<string, unknown>): Promise<T> {
  const store = (client.entities as any)[entity];
  const response = await store.update({ id: String(id), data });
  return response.data as T;
}

export async function deleteEntity(entity: string, id: number): Promise<void> {
  const store = (client.entities as any)[entity];
  await store.delete({ id: String(id) });
}
/* eslint-enable @typescript-eslint/no-explicit-any */

/* ----------------------------------------------------------- 표시 유틸 */
export function fmtTime(value?: string | null): string {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '—';
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

export function todayISO(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

export function shiftDays(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00`);
  d.setDate(d.getDate() + days);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

/* --------------------------------------------- 코드 → 번역키 매핑 (i18n) */
export const STATUS_KEY = {
  normal: 'status.normal',
  late: 'status.late',
  early_leave: 'status.early_leave',
  absent: 'status.absent',
  leave: 'status.leave',
  holiday_work: 'status.holiday_work',
  business_trip: 'status.business_trip',
} as const;

export const CONFIRM_KEY = {
  draft: 'confirm.draft',
  submitted: 'confirm.submitted',
  manager_approved: 'confirm.manager_approved',
  ceo_approved: 'confirm.ceo_approved',
  rejected: 'confirm.rejected',
} as const;

export const STEP_KEY = {
  hr: 'step.hr',
  manager: 'step.manager',
  ceo: 'step.ceo',
  completed: 'step.completed',
  rejected: 'step.rejected',
} as const;

export const DOC_TYPE_KEY = {
  daily_close: 'docType.daily_close',
  weekend_work: 'docType.weekend_work',
  leave_request: 'docType.leave_request',
  overtime_convert: 'docType.overtime_convert',
} as const;

export const DAY_TYPE_KEY = {
  weekday: 'dayType.weekday',
  saturday: 'dayType.saturday',
  sunday: 'dayType.sunday',
  holiday: 'dayType.holiday',
} as const;

export const LEAVE_TYPE_KEY = {
  annual: 'leaveType.annual',
  statutory: 'leaveType.statutory',
  sick: 'leaveType.sick',
  special: 'leaveType.special',
  converted: 'leaveType.converted',
} as const;

export const ROLE_KEY = {
  employee: 'role.employee',
  hr: 'role.hr',
  manager: 'role.manager',
  ceo: 'role.ceo',
} as const;

export const CYCLE_KEY = {
  weekly: 'cycle.weekly',
  biweekly: 'cycle.biweekly',
  monthly: 'cycle.monthly',
} as const;

export const TXN_KEY = {
  earn: 'txn.earn',
  convert_leave: 'txn.convert_leave',
  offset_late: 'txn.offset_late',
  expire: 'txn.expire',
  adjust: 'txn.adjust',
} as const;

export const CATEGORY_KEY = {
  late: 'category.late',
  early_leave: 'category.early_leave',
  absent: 'category.absent',
  leave: 'category.leave',
  holiday_work: 'category.holiday_work',
  business_trip: 'category.business_trip',
  etc: 'category.etc',
} as const;

export const PAY_EFFECT_KEY = {
  paid: 'payEffect.paid',
  unpaid: 'payEffect.unpaid',
  deduct: 'payEffect.deduct',
  premium: 'payEffect.premium',
} as const;