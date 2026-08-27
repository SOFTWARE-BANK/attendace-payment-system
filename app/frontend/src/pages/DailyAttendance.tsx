import { useCallback, useEffect, useMemo, useState } from 'react';
import { CalendarClock, History, Loader2, Lock, PencilLine, RefreshCw, Send, Split } from 'lucide-react';
import { toast } from 'sonner';
import AppShell from '@/components/AppShell';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Textarea } from '@/components/ui/textarea';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  AttendanceReason,
  CONFIRM_KEY,
  DAY_TYPE_KEY,
  DailyAttendance as DailyRow,
  STATUS_KEY,
  apiError,
  callApi,
  fmtTime,
  queryAll,
  todayISO,
} from '@/lib/api';
import { useSession } from '@/hooks/useSession';
import { TransKey, useI18n } from '@/lib/i18n';

function statusVariant(status?: string): 'default' | 'secondary' | 'destructive' | 'outline' {
  if (status === 'normal') return 'secondary';
  if (status === 'late' || status === 'early_leave') return 'destructive';
  if (status === 'absent') return 'destructive';
  if (status === 'holiday_work') return 'default';
  return 'outline';
}

export default function DailyAttendancePage() {
  const { actor, employees } = useSession();
  const { t, fmtMinutes, fmtCount } = useI18n();
  const [workDate, setWorkDate] = useState(() => todayISO());
  const [rows, setRows] = useState<DailyRow[]>([]);
  const [reasons, setReasons] = useState<AttendanceReason[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [deptFilter, setDeptFilter] = useState('all');
  const [editing, setEditing] = useState<DailyRow | null>(null);
  const [editIn, setEditIn] = useState('');
  const [editOut, setEditOut] = useState('');
  const [editReason, setEditReason] = useState('');
  const [editNote, setEditNote] = useState('');
  const [offsetTarget, setOffsetTarget] = useState<DailyRow | null>(null);
  const [offsetMinutes, setOffsetMinutes] = useState('0');
  const [offsetBalance, setOffsetBalance] = useState(0);
  const [historyRow, setHistoryRow] = useState<DailyRow | null>(null);

  const departments = useMemo(() => [...new Set(employees.map((e) => e.department))], [employees]);

  const load = useCallback(async (targetDate: string) => {
    setLoading(true);
    try {
      const [attendance, reasonRows] = await Promise.all([
        queryAll<DailyRow>('daily_attendances', { query: { work_date: targetDate }, sort: 'emp_no', limit: 300 }),
        queryAll<AttendanceReason>('attendance_reasons', { sort: 'sort_order', limit: 100 }),
      ]);
      setRows(attendance);
      setReasons(reasonRows);
    } catch (e) {
      toast.error(apiError(e, t('daily.loadFail')));
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    void load(workDate);
  }, [load, workDate]);

  const filtered = useMemo(
    () => rows.filter((r) => deptFilter === 'all' || r.department === deptFilter),
    [rows, deptFilter],
  );

  const stats = useMemo(() => {
    const total = filtered.length;
    return {
      total,
      late: filtered.filter((r) => (r.late_minutes ?? 0) > 0).length,
      absent: filtered.filter((r) => r.status === 'absent').length,
      overtime: filtered.reduce((sum, r) => sum + (r.overtime_minutes ?? 0), 0),
      draft: filtered.filter((r) => (r.confirm_status ?? 'draft') === 'draft').length,
      locked: filtered.filter((r) => r.locked).length,
    };
  }, [filtered]);

  const runSettle = async () => {
    setBusy('settle');
    try {
      const result = await callApi<{ created: number; updated: number; locked_skipped: number }>(
        '/api/v1/attendance/settle',
        'POST',
        { work_date: workDate },
      );
      toast.success(t('daily.settleOk'), {
        description: t('daily.settleOkDesc', {
          a: fmtCount(result.created),
          b: fmtCount(result.updated),
          c: fmtCount(result.locked_skipped),
        }),
      });
      await load(workDate);
    } catch (e) {
      toast.error(apiError(e, t('daily.settleFail')));
    } finally {
      setBusy('');
    }
  };

  const submitClose = async () => {
    if (!actor) {
      toast.error(t('daily.needActor'));
      return;
    }
    setBusy('submit');
    try {
      const result = await callApi<{ approval_id: number; doc_no: string; record_count: number }>(
        '/api/v1/attendance/approval/submit_daily_close',
        'POST',
        {
          work_date: workDate,
          requester_emp_no: actor.emp_no,
          department: deptFilter === 'all' ? null : deptFilter,
        },
      );
      toast.success(t('daily.submitOk', { doc: result.doc_no }), {
        description: t('daily.submitOkDesc', { n: fmtCount(result.record_count) }),
      });
      await load(workDate);
    } catch (e) {
      toast.error(apiError(e, t('daily.submitFail')));
    } finally {
      setBusy('');
    }
  };

  const openEdit = (row: DailyRow) => {
    setEditing(row);
    setEditIn(row.check_in ? row.check_in.slice(0, 16) : `${row.work_date}T09:00`);
    setEditOut(row.check_out ? row.check_out.slice(0, 16) : `${row.work_date}T18:00`);
    setEditReason(row.reason_code ?? '');
    setEditNote(row.reason_note ?? '');
  };

  const saveEdit = async () => {
    if (!editing || !actor) return;
    setBusy('adjust');
    try {
      await callApi('/api/v1/attendance/adjust', 'POST', {
        attendance_id: editing.id,
        check_in: editIn ? `${editIn}:00` : null,
        check_out: editOut ? `${editOut}:00` : null,
        reason_code: editReason || null,
        reason_note: editNote || null,
        actor_emp_no: actor.emp_no,
      });
      toast.success(t('daily.adjustOk'), { description: t('daily.adjustOkDesc') });
      setEditing(null);
      await load(workDate);
    } catch (e) {
      toast.error(apiError(e, t('daily.adjustFail')));
    } finally {
      setBusy('');
    }
  };

  const openOffset = async (row: DailyRow) => {
    setOffsetTarget(row);
    const remaining = (row.late_minutes ?? 0) - (row.offset_minutes ?? 0);
    setOffsetMinutes(String(Math.max(remaining, 0)));
    try {
      const result = await callApi<{ balance_minutes: number }>(
        `/api/v1/attendance/overtime/balance?emp_no=${row.emp_no}`,
        'GET',
      );
      setOffsetBalance(result.balance_minutes);
    } catch {
      setOffsetBalance(0);
    }
  };

  const saveOffset = async () => {
    if (!offsetTarget || !actor) return;
    setBusy('offset');
    try {
      const result = await callApi<{ used_minutes: number; balance_after: number }>(
        '/api/v1/attendance/overtime/offset_late',
        'POST',
        { attendance_id: offsetTarget.id, minutes: Number(offsetMinutes), actor_emp_no: actor.emp_no },
      );
      toast.success(t('daily.offsetOk', { n: result.used_minutes }), {
        description: t('daily.offsetOkDesc', { a: fmtMinutes(result.balance_after) }),
      });
      setOffsetTarget(null);
      await load(workDate);
    } catch (e) {
      toast.error(apiError(e, t('daily.offsetFail')));
    } finally {
      setBusy('');
    }
  };

  const history = useMemo(() => {
    if (!historyRow?.adjust_history) return [];
    try {
      const parsed = JSON.parse(historyRow.adjust_history);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }, [historyRow]);

  return (
    <AppShell
      title={t('nav.daily')}
      description={t('daily.desc')}
      actions={
        <Button variant="outline" size="sm" onClick={() => void load(workDate)} disabled={loading}>
          <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          {t('common.refresh')}
        </Button>
      }
    >
      <div className="space-y-6">
        <Card>
          <CardContent className="flex flex-wrap items-end gap-3 pt-6">
            <div className="space-y-1.5">
              <Label htmlFor="wd" className="text-xs">
                {t('daily.dateLabel')}
              </Label>
              <Input id="wd" type="date" value={workDate} onChange={(e) => setWorkDate(e.target.value)} className="w-40" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">{t('common.department')}</Label>
              <Select value={deptFilter} onValueChange={setDeptFilter}>
                <SelectTrigger className="w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t('daily.allDept')}</SelectItem>
                  {departments.map((d) => (
                    <SelectItem key={d} value={d}>
                      {d}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button onClick={() => void runSettle()} disabled={busy === 'settle'}>
              {busy === 'settle' ? (
                <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
              ) : (
                <CalendarClock className="mr-1.5 h-4 w-4" />
              )}
              {t('daily.settleBtn')}
            </Button>
            <Button variant="secondary" onClick={() => void submitClose()} disabled={busy === 'submit' || stats.draft === 0}>
              {busy === 'submit' ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : <Send className="mr-1.5 h-4 w-4" />}
              {t('daily.submitBtn', { n: fmtCount(stats.draft) })}
            </Button>
          </CardContent>
        </Card>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          {[
            { label: t('daily.stat.total'), value: fmtCount(stats.total) },
            { label: t('daily.stat.late'), value: fmtCount(stats.late) },
            { label: t('daily.stat.absent'), value: fmtCount(stats.absent) },
            { label: t('daily.stat.overtime'), value: fmtMinutes(stats.overtime) },
            { label: t('daily.stat.locked'), value: fmtCount(stats.locked) },
          ].map((s) => (
            <Card key={s.label}>
              <CardContent className="pt-6">
                <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{s.label}</p>
                <p className="num mt-1.5 text-xl font-bold">{s.value}</p>
              </CardContent>
            </Card>
          ))}
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t('daily.listTitle')}</CardTitle>
            <CardDescription>{t('daily.listDesc')}</CardDescription>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            {loading ? (
              <div className="space-y-2">
                {[0, 1, 2, 3, 4].map((i) => (
                  <Skeleton key={i} className="h-11 w-full" />
                ))}
              </div>
            ) : filtered.length === 0 ? (
              <div className="rounded-md border border-dashed border-border py-12 text-center">
                <CalendarClock className="mx-auto h-7 w-7 text-muted-foreground" />
                <p className="mt-2 text-sm font-medium">{t('daily.emptyTitle')}</p>
                <p className="mt-1 text-xs text-muted-foreground">{t('daily.emptyHint')}</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t('common.employee')}</TableHead>
                    <TableHead>{t('daily.th.kind')}</TableHead>
                    <TableHead>{t('daily.th.raw')}</TableHead>
                    <TableHead>{t('daily.th.fixed')}</TableHead>
                    <TableHead className="text-right">{t('daily.th.work')}</TableHead>
                    <TableHead className="text-right">{t('daily.th.otHoliday')}</TableHead>
                    <TableHead className="text-right">{t('daily.th.lateOffset')}</TableHead>
                    <TableHead>{t('common.status')}</TableHead>
                    <TableHead>{t('daily.th.approval')}</TableHead>
                    <TableHead className="text-right">{t('daily.th.action')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell>
                        <div className="font-medium">{r.employee_name}</div>
                        <div className="text-xs text-muted-foreground">
                          {r.emp_no} · {r.department}
                        </div>
                      </TableCell>
                      <TableCell className="text-xs">
                        {t((DAY_TYPE_KEY[(r.day_type ?? 'weekday') as keyof typeof DAY_TYPE_KEY] ??
                          'dayType.weekday') as TransKey)}
                      </TableCell>
                      <TableCell className="num text-xs text-muted-foreground">
                        {fmtTime(r.raw_check_in)} ~ {fmtTime(r.raw_check_out)}
                        <span className="ml-1">({fmtCount(r.log_count ?? 0)})</span>
                      </TableCell>
                      <TableCell className="num text-sm">
                        {fmtTime(r.check_in)} ~ {fmtTime(r.check_out)}
                        {r.adjusted ? (
                          <Badge variant="outline" className="ml-1.5 text-[10px]">
                            {t('daily.adjustedTag')}
                          </Badge>
                        ) : null}
                      </TableCell>
                      <TableCell className="num text-right text-sm">{fmtMinutes(r.work_minutes)}</TableCell>
                      <TableCell className="num text-right text-sm">
                        {fmtMinutes((r.overtime_minutes ?? 0) + (r.holiday_minutes ?? 0))}
                      </TableCell>
                      <TableCell className="num text-right text-sm">
                        {(r.late_minutes ?? 0) > 0 ? (
                          <span className="text-destructive">{fmtMinutes(r.late_minutes)}</span>
                        ) : (
                          '—'
                        )}
                        {(r.offset_minutes ?? 0) > 0 ? (
                          <span className="ml-1 text-primary">(-{fmtMinutes(r.offset_minutes)})</span>
                        ) : null}
                      </TableCell>
                      <TableCell>
                        <Badge variant={statusVariant(r.status)}>
                          {t((STATUS_KEY[(r.status ?? 'normal') as keyof typeof STATUS_KEY] ??
                            'status.normal') as TransKey)}
                        </Badge>
                        {r.reason_code ? (
                          <div className="mt-1 text-[11px] text-muted-foreground">{r.reason_code}</div>
                        ) : null}
                      </TableCell>
                      <TableCell className="text-xs">
                        <span className={r.locked ? 'font-medium text-primary' : 'text-muted-foreground'}>
                          {t((CONFIRM_KEY[(r.confirm_status ?? 'draft') as keyof typeof CONFIRM_KEY] ??
                            'confirm.draft') as TransKey)}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => openEdit(r)}
                            disabled={r.locked}
                            title={r.locked ? t('daily.lockedTip') : t('daily.adjustTip')}
                          >
                            {r.locked ? <Lock className="h-3.5 w-3.5" /> : <PencilLine className="h-3.5 w-3.5" />}
                          </Button>
                          {(r.late_minutes ?? 0) > (r.offset_minutes ?? 0) && !r.locked ? (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => void openOffset(r)}
                              title={t('daily.offsetTip')}
                            >
                              <Split className="h-3.5 w-3.5" />
                            </Button>
                          ) : null}
                          {r.adjust_history && r.adjust_history !== '[]' ? (
                            <Button size="sm" variant="ghost" onClick={() => setHistoryRow(r)} title={t('daily.historyTip')}>
                              <History className="h-3.5 w-3.5" />
                            </Button>
                          ) : null}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>

      <Dialog open={editing !== null} onOpenChange={(open) => !open && setEditing(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('daily.dlg.adjustTitle', { name: editing?.employee_name ?? '' })}</DialogTitle>
            <DialogDescription>
              {t('daily.dlg.adjustDesc', {
                date: editing?.work_date ?? '',
                a: fmtTime(editing?.raw_check_in),
                b: fmtTime(editing?.raw_check_out),
              })}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="ein" className="text-xs">
                  {t('daily.dlg.checkIn')}
                </Label>
                <Input id="ein" type="datetime-local" value={editIn} onChange={(e) => setEditIn(e.target.value)} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="eout" className="text-xs">
                  {t('daily.dlg.checkOut')}
                </Label>
                <Input id="eout" type="datetime-local" value={editOut} onChange={(e) => setEditOut(e.target.value)} />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">{t('daily.dlg.reason')}</Label>
              <Select value={editReason} onValueChange={setEditReason}>
                <SelectTrigger>
                  <SelectValue placeholder={t('daily.dlg.reasonPlaceholder')} />
                </SelectTrigger>
                <SelectContent>
                  {reasons.map((r) => (
                    <SelectItem key={r.code} value={r.code}>
                      {r.name} ({r.code})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="enote" className="text-xs">
                {t('daily.dlg.noteLabel')}
              </Label>
              <Textarea id="enote" value={editNote} onChange={(e) => setEditNote(e.target.value)} rows={3} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditing(null)}>
              {t('common.cancel')}
            </Button>
            <Button onClick={() => void saveEdit()} disabled={busy === 'adjust'}>
              {busy === 'adjust' ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : null}
              {t('daily.dlg.saveAdjust')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={offsetTarget !== null} onOpenChange={(open) => !open && setOffsetTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('daily.dlg.offsetTitle', { name: offsetTarget?.employee_name ?? '' })}</DialogTitle>
            <DialogDescription>
              {t('daily.dlg.offsetDesc', {
                a: fmtMinutes(offsetTarget?.late_minutes),
                b: fmtMinutes((offsetTarget?.late_minutes ?? 0) - (offsetTarget?.offset_minutes ?? 0)),
                c: fmtMinutes(offsetBalance),
              })}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-1.5">
            <Label htmlFor="offm" className="text-xs">
              {t('daily.dlg.offsetLabel')}
            </Label>
            <Input
              id="offm"
              type="number"
              min={1}
              value={offsetMinutes}
              onChange={(e) => setOffsetMinutes(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">{t('daily.dlg.offsetHint')}</p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOffsetTarget(null)}>
              {t('common.cancel')}
            </Button>
            <Button onClick={() => void saveOffset()} disabled={busy === 'offset' || offsetBalance <= 0}>
              {busy === 'offset' ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : null}
              {t('daily.dlg.offsetRun')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={historyRow !== null} onOpenChange={(open) => !open && setHistoryRow(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('daily.dlg.historyTitle', { name: historyRow?.employee_name ?? '' })}</DialogTitle>
            <DialogDescription>{t('daily.dlg.historyDesc', { date: historyRow?.work_date ?? '' })}</DialogDescription>
          </DialogHeader>
          <div className="max-h-80 space-y-3 overflow-y-auto">
            {history.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t('daily.noHistory')}</p>
            ) : (
              history.map((h: Record<string, unknown>, i: number) => {
                const before = (h.before ?? {}) as Record<string, string | null>;
                const after = (h.after ?? {}) as Record<string, string | null>;
                return (
                  <div key={i} className="rounded-md border border-border p-3 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{String(h.by ?? '')}</span>
                      <span className="text-muted-foreground">{String(h.at ?? '').replace('T', ' ')}</span>
                    </div>
                    <div className="mt-2 grid gap-1 text-muted-foreground">
                      <div>
                        {t('daily.before')}: {fmtTime(before.check_in)} ~ {fmtTime(before.check_out)} /{' '}
                        {before.reason_code ?? '-'}
                      </div>
                      <div className="text-foreground">
                        {t('daily.after')}: {fmtTime(after.check_in)} ~ {fmtTime(after.check_out)} /{' '}
                        {after.reason_code ?? '-'}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}