import { useCallback, useEffect, useMemo, useState } from 'react';
import { CalendarPlus, Loader2, Plane, RefreshCw, Sun } from 'lucide-react';
import { toast } from 'sonner';
import AppShell from '@/components/AppShell';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Skeleton } from '@/components/ui/skeleton';
import { Progress } from '@/components/ui/progress';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  DAY_TYPE_KEY,
  LEAVE_TYPE_KEY,
  LeaveBalance,
  LeaveRequest,
  WeekendWorkRequest,
  apiError,
  callApi,
  queryAll,
  todayISO,
} from '@/lib/api';
import { useSession } from '@/hooks/useSession';
import { TransKey, useI18n } from '@/lib/i18n';

export default function LeaveManagement() {
  const { employees, actor } = useSession();
  const { t, fmtMinutes, fmtDays, fmtCount } = useI18n();
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [requests, setRequests] = useState<LeaveRequest[]>([]);
  const [weekend, setWeekend] = useState<WeekendWorkRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');

  const [empNo, setEmpNo] = useState('');
  const [leaveType, setLeaveType] = useState('annual');
  const [start, setStart] = useState(() => todayISO());
  const [end, setEnd] = useState(() => todayISO());
  const [halfDay, setHalfDay] = useState('full');
  const [reason, setReason] = useState('');

  const [wEmpNo, setWEmpNo] = useState('');
  const [wDate, setWDate] = useState(() => todayISO());
  const [wStart, setWStart] = useState('09:00');
  const [wEnd, setWEnd] = useState('14:00');
  const [wRate, setWRate] = useState('1.5');
  const [wReason, setWReason] = useState('');

  const statusBadge = (status?: string) => {
    if (status === 'approved') return <Badge className="bg-primary">{t('badge.approved')}</Badge>;
    if (status === 'rejected') return <Badge variant="destructive">{t('badge.rejected')}</Badge>;
    if (status === 'pending') return <Badge variant="secondary">{t('badge.inApproval')}</Badge>;
    return <Badge variant="outline">{t('badge.drafting')}</Badge>;
  };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [b, r, w] = await Promise.all([
        queryAll<LeaveBalance>('leave_balances', { sort: 'emp_no', limit: 300 }),
        queryAll<LeaveRequest>('leave_requests', { sort: '-id', limit: 200 }),
        queryAll<WeekendWorkRequest>('weekend_work_requests', { sort: '-id', limit: 200 }),
      ]);
      setBalances(b);
      setRequests(r);
      setWeekend(w);
    } catch (e) {
      toast.error(apiError(e, t('leave.loadFail')));
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!empNo && actor) setEmpNo(actor.emp_no);
    if (!wEmpNo && actor) setWEmpNo(actor.emp_no);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [actor]);

  const selectedBalance = useMemo(
    () => balances.find((b) => b.emp_no === empNo && b.leave_type === leaveType),
    [balances, empNo, leaveType],
  );

  const remaining = selectedBalance
    ? Number(selectedBalance.granted_days ?? 0) -
      Number(selectedBalance.used_days ?? 0) -
      Number(selectedBalance.pending_days ?? 0)
    : 0;

  const requestDays = useMemo(() => {
    if (halfDay !== 'full') return 0.5;
    const s = new Date(`${start}T00:00:00`);
    const e = new Date(`${end}T00:00:00`);
    const diff = Math.floor((e.getTime() - s.getTime()) / 86400000) + 1;
    return diff > 0 ? diff : 0;
  }, [start, end, halfDay]);

  const applyLeave = async () => {
    if (!empNo) {
      toast.error(t('leave.needEmp'));
      return;
    }
    setBusy('leave');
    try {
      const result = await callApi<{ leave_request_id: number; days: number; doc_no: string }>(
        '/api/v1/attendance/leave/apply',
        'POST',
        {
          emp_no: empNo,
          leave_type: leaveType,
          start_date: start,
          end_date: end,
          half_day_type: halfDay,
          reason,
        },
      );
      toast.success(t('leave.applyOk', { doc: result.doc_no }), {
        description: t('leave.applyOkDesc', { days: fmtDays(result.days) }),
      });
      setReason('');
      await load();
    } catch (e) {
      toast.error(apiError(e, t('leave.applyFail')));
    } finally {
      setBusy('');
    }
  };

  const applyWeekend = async () => {
    if (!wEmpNo) {
      toast.error(t('leave.needEmp'));
      return;
    }
    setBusy('weekend');
    try {
      const result = await callApi<{ weekend_request_id: number; planned_minutes: number; doc_no: string }>(
        '/api/v1/attendance/weekend/apply',
        'POST',
        {
          emp_no: wEmpNo,
          work_date: wDate,
          planned_start: wStart,
          planned_end: wEnd,
          premium_rate: Number(wRate),
          reason: wReason,
        },
      );
      toast.success(t('leave.weekendOk', { doc: result.doc_no }), {
        description: t('leave.weekendOkDesc', { a: fmtMinutes(result.planned_minutes) }),
      });
      setWReason('');
      await load();
    } catch (e) {
      toast.error(apiError(e, t('leave.weekendFail')));
    } finally {
      setBusy('');
    }
  };

  return (
    <AppShell
      title={t('nav.leave')}
      description={t('leave.desc')}
      actions={
        <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
          <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          {t('common.refresh')}
        </Button>
      }
    >
      <Tabs defaultValue="leave" className="space-y-6">
        <TabsList>
          <TabsTrigger value="leave">{t('leave.tab.request')}</TabsTrigger>
          <TabsTrigger value="balance">{t('leave.tab.balance')}</TabsTrigger>
          <TabsTrigger value="weekend">{t('leave.tab.weekend')}</TabsTrigger>
        </TabsList>

        <TabsContent value="leave" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-5">
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle className="text-base">{t('leave.formTitle')}</CardTitle>
                <CardDescription>{t('leave.formDesc')}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="space-y-1.5">
                  <Label className="text-xs">{t('leave.applicant')}</Label>
                  <Select value={empNo} onValueChange={setEmpNo}>
                    <SelectTrigger>
                      <SelectValue placeholder={t('common.selectEmployee')} />
                    </SelectTrigger>
                    <SelectContent>
                      {employees.map((e) => (
                        <SelectItem key={e.emp_no} value={e.emp_no}>
                          {e.name} · {e.department}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">{t('leave.typeLabel')}</Label>
                  <Select value={leaveType} onValueChange={setLeaveType}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="annual">{t('leave.type.annual')}</SelectItem>
                      <SelectItem value="sick">{t('leave.type.sick')}</SelectItem>
                      <SelectItem value="converted">{t('leave.type.converted')}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="space-y-1.5">
                    <Label htmlFor="ls" className="text-xs">
                      {t('leave.startDate')}
                    </Label>
                    <Input id="ls" type="date" value={start} onChange={(e) => setStart(e.target.value)} />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="le" className="text-xs">
                      {t('leave.endDate')}
                    </Label>
                    <Input id="le" type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">{t('leave.unitLabel')}</Label>
                  <Select value={halfDay} onValueChange={setHalfDay}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="full">{t('leave.unit.full')}</SelectItem>
                      <SelectItem value="am">{t('leave.unit.am')}</SelectItem>
                      <SelectItem value="pm">{t('leave.unit.pm')}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="lr" className="text-xs">
                    {t('leave.reasonLabel')}
                  </Label>
                  <Textarea id="lr" value={reason} onChange={(e) => setReason(e.target.value)} rows={3} />
                </div>
                <div className="rounded-md bg-muted px-3 py-2 text-xs">
                  <span className={remaining < requestDays ? 'text-destructive' : ''}>
                    {t('leave.summary', { a: fmtDays(requestDays), b: fmtDays(remaining) })}
                  </span>
                  {selectedBalance ? (
                    <span className="text-muted-foreground">
                      {' '}
                      {t('leave.summaryDetail', {
                        a: fmtDays(selectedBalance.granted_days ?? 0),
                        b: fmtDays(selectedBalance.used_days ?? 0),
                      })}
                    </span>
                  ) : (
                    <span className="text-muted-foreground"> {t('leave.noBalance')}</span>
                  )}
                </div>
                <Button onClick={() => void applyLeave()} disabled={busy === 'leave'} className="w-full">
                  {busy === 'leave' ? (
                    <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                  ) : (
                    <CalendarPlus className="mr-1.5 h-4 w-4" />
                  )}
                  {t('leave.submitBtn')}
                </Button>
              </CardContent>
            </Card>

            <Card className="lg:col-span-3">
              <CardHeader>
                <CardTitle className="text-base">{t('leave.listTitle')}</CardTitle>
                <CardDescription>{t('leave.listDesc')}</CardDescription>
              </CardHeader>
              <CardContent className="overflow-x-auto">
                {loading ? (
                  <div className="space-y-2">
                    {[0, 1, 2].map((i) => (
                      <Skeleton key={i} className="h-10 w-full" />
                    ))}
                  </div>
                ) : requests.length === 0 ? (
                  <div className="rounded-md border border-dashed border-border py-10 text-center">
                    <Plane className="mx-auto h-7 w-7 text-muted-foreground" />
                    <p className="mt-2 text-sm font-medium">{t('leave.emptyTitle')}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{t('leave.emptyHint')}</p>
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>{t('common.employee')}</TableHead>
                        <TableHead>{t('common.type')}</TableHead>
                        <TableHead>{t('common.period')}</TableHead>
                        <TableHead className="text-right">{t('leave.th.days')}</TableHead>
                        <TableHead>{t('common.status')}</TableHead>
                        <TableHead>{t('leave.th.reflected')}</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {requests.map((r) => (
                        <TableRow key={r.id}>
                          <TableCell>
                            <div className="font-medium">{r.employee_name}</div>
                            <div className="text-xs text-muted-foreground">{r.department}</div>
                          </TableCell>
                          <TableCell className="text-sm">
                            {LEAVE_TYPE_KEY[r.leave_type as keyof typeof LEAVE_TYPE_KEY]
                              ? t(LEAVE_TYPE_KEY[r.leave_type as keyof typeof LEAVE_TYPE_KEY] as TransKey)
                              : r.leave_type}
                          </TableCell>
                          <TableCell className="num text-sm">
                            {r.start_date} ~ {r.end_date}
                          </TableCell>
                          <TableCell className="num text-right">{fmtDays(r.days ?? 0)}</TableCell>
                          <TableCell>{statusBadge(r.status)}</TableCell>
                          <TableCell className="text-xs">
                            {r.reflected ? (
                              <span className="text-primary">
                                {t('leave.reflectedCount', { n: fmtCount(r.reflected_count ?? 0) })}
                              </span>
                            ) : (
                              <span className="text-muted-foreground">{t('leave.notReflected')}</span>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="balance">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t('leave.balanceTitle')}</CardTitle>
              <CardDescription>{t('leave.balanceDesc')}</CardDescription>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              {loading ? (
                <div className="space-y-2">
                  {[0, 1, 2, 3].map((i) => (
                    <Skeleton key={i} className="h-10 w-full" />
                  ))}
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t('common.employee')}</TableHead>
                      <TableHead>{t('common.department')}</TableHead>
                      <TableHead>{t('common.type')}</TableHead>
                      <TableHead className="text-right">{t('leave.th.granted')}</TableHead>
                      <TableHead className="text-right">{t('leave.th.used')}</TableHead>
                      <TableHead className="text-right">{t('leave.th.pending')}</TableHead>
                      <TableHead className="text-right">{t('leave.th.converted')}</TableHead>
                      <TableHead className="w-40">{t('leave.th.remaining')}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {balances.map((b) => {
                      const granted = Number(b.granted_days ?? 0);
                      const used = Number(b.used_days ?? 0);
                      const pending = Number(b.pending_days ?? 0);
                      const rest = granted - used - pending;
                      const pct = granted > 0 ? Math.max(0, Math.min(100, (rest / granted) * 100)) : 0;
                      return (
                        <TableRow key={b.id}>
                          <TableCell className="font-medium">{b.employee_name}</TableCell>
                          <TableCell className="text-sm">{b.department}</TableCell>
                          <TableCell className="text-sm">
                            {LEAVE_TYPE_KEY[b.leave_type as keyof typeof LEAVE_TYPE_KEY]
                              ? t(LEAVE_TYPE_KEY[b.leave_type as keyof typeof LEAVE_TYPE_KEY] as TransKey)
                              : b.leave_type}
                          </TableCell>
                          <TableCell className="num text-right">{fmtDays(granted)}</TableCell>
                          <TableCell className="num text-right">{fmtDays(used)}</TableCell>
                          <TableCell className="num text-right">{fmtDays(pending)}</TableCell>
                          <TableCell className="num text-right text-primary">
                            {fmtDays(b.converted_days ?? 0)}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Progress value={pct} className="h-2" />
                              <span className="num w-14 shrink-0 text-right text-xs font-medium">{fmtDays(rest)}</span>
                            </div>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="weekend" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-5">
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle className="text-base">{t('leave.weekendFormTitle')}</CardTitle>
                <CardDescription>{t('leave.weekendFormDesc')}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="space-y-1.5">
                  <Label className="text-xs">{t('leave.weekendEmp')}</Label>
                  <Select value={wEmpNo} onValueChange={setWEmpNo}>
                    <SelectTrigger>
                      <SelectValue placeholder={t('common.selectEmployee')} />
                    </SelectTrigger>
                    <SelectContent>
                      {employees.map((e) => (
                        <SelectItem key={e.emp_no} value={e.emp_no}>
                          {e.name} · {e.department}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="wd" className="text-xs">
                    {t('leave.weekendDate')}
                  </Label>
                  <Input id="wd" type="date" value={wDate} onChange={(e) => setWDate(e.target.value)} />
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="space-y-1.5">
                    <Label htmlFor="ws" className="text-xs">
                      {t('leave.weekendStart')}
                    </Label>
                    <Input id="ws" type="time" value={wStart} onChange={(e) => setWStart(e.target.value)} />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="we" className="text-xs">
                      {t('leave.weekendEnd')}
                    </Label>
                    <Input id="we" type="time" value={wEnd} onChange={(e) => setWEnd(e.target.value)} />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="wr" className="text-xs">
                    {t('leave.weekendRate')}
                  </Label>
                  <Input id="wr" type="number" step="0.1" min="1" value={wRate} onChange={(e) => setWRate(e.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="wrs" className="text-xs">
                    {t('leave.weekendReason')}
                  </Label>
                  <Textarea id="wrs" value={wReason} onChange={(e) => setWReason(e.target.value)} rows={3} />
                </div>
                <Button onClick={() => void applyWeekend()} disabled={busy === 'weekend'} className="w-full">
                  {busy === 'weekend' ? (
                    <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                  ) : (
                    <Sun className="mr-1.5 h-4 w-4" />
                  )}
                  {t('leave.weekendSubmit')}
                </Button>
              </CardContent>
            </Card>

            <Card className="lg:col-span-3">
              <CardHeader>
                <CardTitle className="text-base">{t('leave.weekendListTitle')}</CardTitle>
                <CardDescription>{t('leave.weekendListDesc')}</CardDescription>
              </CardHeader>
              <CardContent className="overflow-x-auto">
                {loading ? (
                  <div className="space-y-2">
                    {[0, 1, 2].map((i) => (
                      <Skeleton key={i} className="h-10 w-full" />
                    ))}
                  </div>
                ) : weekend.length === 0 ? (
                  <div className="rounded-md border border-dashed border-border py-10 text-center">
                    <Sun className="mx-auto h-7 w-7 text-muted-foreground" />
                    <p className="mt-2 text-sm font-medium">{t('leave.weekendEmptyTitle')}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{t('leave.weekendEmptyHint')}</p>
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>{t('common.employee')}</TableHead>
                        <TableHead>{t('leave.th.workDate')}</TableHead>
                        <TableHead>{t('leave.th.planned')}</TableHead>
                        <TableHead className="text-right">{t('leave.th.actual')}</TableHead>
                        <TableHead className="text-right">{t('leave.th.rate')}</TableHead>
                        <TableHead>{t('common.status')}</TableHead>
                        <TableHead>{t('leave.th.matched')}</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {weekend.map((w) => (
                        <TableRow key={w.id}>
                          <TableCell>
                            <div className="font-medium">{w.employee_name}</div>
                            <div className="text-xs text-muted-foreground">{w.department}</div>
                          </TableCell>
                          <TableCell className="num text-sm">
                            {w.work_date}
                            <div className="text-xs text-muted-foreground">
                              {t(
                                (DAY_TYPE_KEY[(w.day_type ?? 'holiday') as keyof typeof DAY_TYPE_KEY] ??
                                  'dayType.holiday') as TransKey,
                              )}
                            </div>
                          </TableCell>
                          <TableCell className="num text-sm">
                            {w.planned_start}~{w.planned_end}
                            <div className="text-xs text-muted-foreground">{fmtMinutes(w.planned_minutes)}</div>
                          </TableCell>
                          <TableCell className="num text-right text-sm">{fmtMinutes(w.actual_minutes)}</TableCell>
                          <TableCell className="num text-right text-sm">×{w.premium_rate ?? 1.5}</TableCell>
                          <TableCell>{statusBadge(w.status)}</TableCell>
                          <TableCell className="text-xs">
                            {w.matched ? (
                              <span className="text-primary">{t('leave.matched')}</span>
                            ) : (
                              <span className="text-muted-foreground">{t('leave.notMatched')}</span>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </AppShell>
  );
}