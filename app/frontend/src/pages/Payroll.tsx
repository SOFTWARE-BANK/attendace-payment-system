import { useCallback, useEffect, useMemo, useState } from 'react';
import { Calculator, Download, Loader2, RefreshCw, Wallet } from 'lucide-react';
import { toast } from 'sonner';
import AppShell from '@/components/AppShell';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  CYCLE_KEY,
  PayrollItem,
  PayrollRun,
  apiError,
  callApi,
  queryAll,
  shiftDays,
  todayISO,
} from '@/lib/api';
import { TransKey, useI18n } from '@/lib/i18n';

function defaultPeriod(cycle: string): { start: string; end: string } {
  const today = todayISO();
  if (cycle === 'weekly') return { start: shiftDays(today, -7), end: shiftDays(today, -1) };
  if (cycle === 'biweekly') return { start: shiftDays(today, -14), end: shiftDays(today, -1) };
  return { start: shiftDays(today, -30), end: shiftDays(today, -1) };
}

export default function PayrollPage() {
  const { t, fmtMinutes, fmtMoney, fmtPeople, fmtDays } = useI18n();
  const [cycle, setCycle] = useState('weekly');
  const [start, setStart] = useState(() => defaultPeriod('weekly').start);
  const [end, setEnd] = useState(() => defaultPeriod('weekly').end);
  const [confirmedOnly, setConfirmedOnly] = useState(true);
  const [runs, setRuns] = useState<PayrollRun[]>([]);
  const [items, setItems] = useState<PayrollItem[]>([]);
  const [activeRun, setActiveRun] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [calculating, setCalculating] = useState(false);

  const cycleLabel = (value?: string | null): string => {
    const key = CYCLE_KEY[(value ?? '') as keyof typeof CYCLE_KEY];
    return key ? t(key as TransKey) : (value ?? '');
  };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [runRows, itemRows] = await Promise.all([
        queryAll<PayrollRun>('payroll_runs', { sort: '-id', limit: 100 }),
        queryAll<PayrollItem>('payroll_items', { sort: '-id', limit: 800 }),
      ]);
      setRuns(runRows);
      setItems(itemRows);
      setActiveRun((prev) => prev ?? runRows[0]?.id ?? null);
    } catch (e) {
      toast.error(apiError(e, t('pay.loadFail')));
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const changeCycle = (value: string) => {
    setCycle(value);
    const p = defaultPeriod(value);
    setStart(p.start);
    setEnd(p.end);
  };

  const calculate = async () => {
    setCalculating(true);
    try {
      const result = await callApi<{ payroll_run_id: number; employee_count: number; total_amount: number }>(
        '/api/v1/attendance/payroll/calculate',
        'POST',
        { pay_cycle: cycle, period_start: start, period_end: end, confirmed_only: confirmedOnly },
      );
      toast.success(t('pay.calcOk'), {
        description: t('pay.calcOkDesc', {
          a: fmtPeople(result.employee_count),
          b: fmtMoney(result.total_amount),
        }),
      });
      setActiveRun(result.payroll_run_id);
      await load();
    } catch (e) {
      toast.error(apiError(e, t('pay.calcFail')));
    } finally {
      setCalculating(false);
    }
  };

  const currentRun = useMemo(() => runs.find((r) => r.id === activeRun) ?? null, [runs, activeRun]);
  const currentItems = useMemo(
    () => items.filter((i) => i.payroll_run_id === activeRun).sort((a, b) => a.emp_no.localeCompare(b.emp_no)),
    [items, activeRun],
  );

  const totals = useMemo(
    () =>
      currentItems.reduce(
        (acc, i) => ({
          base: acc.base + (i.base_pay ?? 0),
          overtime: acc.overtime + (i.overtime_pay ?? 0),
          holiday: acc.holiday + (i.holiday_pay ?? 0),
          night: acc.night + (i.night_pay ?? 0),
          late: acc.late + (i.late_deduction ?? 0),
          offset: acc.offset + (i.offset_credit ?? 0),
          net: acc.net + (i.net_pay ?? 0),
        }),
        { base: 0, overtime: 0, holiday: 0, night: 0, late: 0, offset: 0, net: 0 },
      ),
    [currentItems],
  );

  const exportCsv = () => {
    if (currentItems.length === 0) {
      toast.error(t('pay.exportEmpty'));
      return;
    }
    const header = [
      t('common.empNo'),
      t('common.name'),
      t('common.department'),
      t('pay.th.cycle'),
      t('pay.csv.regularMin'),
      t('pay.csv.otMin'),
      t('pay.csv.holidayMin'),
      t('pay.csv.nightMin'),
      t('pay.csv.lateMin'),
      t('pay.csv.offsetMin'),
      t('pay.csv.absentDays'),
      t('pay.csv.leaveDays'),
      t('pay.th.base'),
      t('pay.csv.otPay'),
      t('pay.csv.holidayPay'),
      t('pay.csv.nightPay'),
      t('pay.csv.lateDeduct'),
      t('pay.csv.offsetCredit'),
      t('pay.th.net'),
    ];
    const lines = currentItems.map((i) =>
      [
        i.emp_no,
        i.employee_name ?? '',
        i.department ?? '',
        cycleLabel(i.pay_cycle),
        i.regular_minutes ?? 0,
        i.overtime_minutes ?? 0,
        i.holiday_minutes ?? 0,
        i.night_minutes ?? 0,
        i.late_minutes ?? 0,
        i.offset_minutes ?? 0,
        i.absent_days ?? 0,
        i.leave_days ?? 0,
        Math.round(i.base_pay ?? 0),
        Math.round(i.overtime_pay ?? 0),
        Math.round(i.holiday_pay ?? 0),
        Math.round(i.night_pay ?? 0),
        Math.round(i.late_deduction ?? 0),
        Math.round(i.offset_credit ?? 0),
        Math.round(i.net_pay ?? 0),
      ].join(','),
    );
    const csv = `\uFEFF${[header.join(','), ...lines].join('\n')}`;
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `payroll_${currentRun?.pay_cycle ?? cycle}_${currentRun?.period_start ?? start}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success(t('pay.exportOk'));
  };

  return (
    <AppShell
      title={t('nav.payroll')}
      description={t('pay.desc')}
      actions={
        <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
          <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          {t('common.refresh')}
        </Button>
      }
    >
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t('pay.runTitle')}</CardTitle>
            <CardDescription>{t('pay.runDesc')}</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap items-end gap-4">
            <div className="space-y-1.5">
              <Label className="text-xs">{t('pay.cycleLabel')}</Label>
              <Select value={cycle} onValueChange={changeCycle}>
                <SelectTrigger className="w-36">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="weekly">{t('cycle.weekly')}</SelectItem>
                  <SelectItem value="biweekly">{t('cycle.biweekly')}</SelectItem>
                  <SelectItem value="monthly">{t('cycle.monthly')}</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ps" className="text-xs">
                {t('pay.periodStart')}
              </Label>
              <Input id="ps" type="date" value={start} onChange={(e) => setStart(e.target.value)} className="w-40" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="pe" className="text-xs">
                {t('pay.periodEnd')}
              </Label>
              <Input id="pe" type="date" value={end} onChange={(e) => setEnd(e.target.value)} className="w-40" />
            </div>
            <div className="flex items-center gap-2 pb-2">
              <Switch id="co" checked={confirmedOnly} onCheckedChange={setConfirmedOnly} />
              <Label htmlFor="co" className="text-xs">
                {t('pay.confirmedOnly')}
              </Label>
            </div>
            <Button onClick={() => void calculate()} disabled={calculating}>
              {calculating ? (
                <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
              ) : (
                <Calculator className="mr-1.5 h-4 w-4" />
              )}
              {t('pay.calcBtn')}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t('pay.historyTitle')}</CardTitle>
            <CardDescription>{t('pay.historyDesc')}</CardDescription>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            {loading ? (
              <div className="space-y-2">
                {[0, 1, 2].map((i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            ) : runs.length === 0 ? (
              <div className="rounded-md border border-dashed border-border py-10 text-center">
                <Wallet className="mx-auto h-7 w-7 text-muted-foreground" />
                <p className="mt-2 text-sm font-medium">{t('pay.historyEmptyTitle')}</p>
                <p className="mt-1 text-xs text-muted-foreground">{t('pay.historyEmptyHint')}</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t('pay.th.runName')}</TableHead>
                    <TableHead>{t('pay.th.cycle')}</TableHead>
                    <TableHead>{t('common.period')}</TableHead>
                    <TableHead className="text-right">{t('pay.th.headcount')}</TableHead>
                    <TableHead className="text-right">{t('pay.th.total')}</TableHead>
                    <TableHead>{t('pay.th.basis')}</TableHead>
                    <TableHead className="text-right">{t('pay.th.select')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {runs.map((r) => (
                    <TableRow key={r.id} className={r.id === activeRun ? 'bg-accent/50' : undefined}>
                      <TableCell className="font-medium">{r.run_name}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{cycleLabel(r.pay_cycle)}</Badge>
                      </TableCell>
                      <TableCell className="num text-sm">
                        {r.period_start} ~ {r.period_end}
                      </TableCell>
                      <TableCell className="num text-right">{fmtPeople(r.employee_count ?? 0)}</TableCell>
                      <TableCell className="num text-right font-medium">{fmtMoney(r.total_amount)}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {r.confirmed_only ? t('pay.basisConfirmed') : t('pay.basisAll')}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button size="sm" variant={r.id === activeRun ? 'default' : 'ghost'} onClick={() => setActiveRun(r.id)}>
                          {t('common.detail')}
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {currentRun ? (
          <>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {[
                { label: t('pay.kpi.base'), value: fmtMoney(totals.base) },
                { label: t('pay.kpi.allowance'), value: fmtMoney(totals.overtime + totals.holiday) },
                {
                  label: t('pay.kpi.late'),
                  value: fmtMoney(totals.late),
                  hint: t('pay.kpi.lateHint', { a: fmtMoney(totals.offset) }),
                },
                { label: t('pay.kpi.net'), value: fmtMoney(totals.net) },
              ].map((s) => (
                <Card key={s.label}>
                  <CardContent className="pt-6">
                    <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{s.label}</p>
                    <p className="num mt-1.5 text-xl font-bold">{s.value}</p>
                    {s.hint ? <p className="mt-1 text-xs text-muted-foreground">{s.hint}</p> : null}
                  </CardContent>
                </Card>
              ))}
            </div>

            <Card>
              <CardHeader className="flex-row items-start justify-between gap-3 space-y-0">
                <div>
                  <CardTitle className="text-base">{t('pay.itemTitle', { name: currentRun.run_name ?? '' })}</CardTitle>
                  <CardDescription>
                    {currentRun.period_start} ~ {currentRun.period_end} ·{' '}
                    {currentRun.confirmed_only ? t('pay.itemDescConfirmed') : t('pay.itemDescAll')}
                  </CardDescription>
                </div>
                <Button variant="outline" size="sm" onClick={exportCsv}>
                  <Download className="mr-1.5 h-3.5 w-3.5" />
                  {t('pay.exportCsv')}
                </Button>
              </CardHeader>
              <CardContent className="overflow-x-auto">
                {currentItems.length === 0 ? (
                  <p className="py-8 text-center text-sm text-muted-foreground">{t('pay.itemEmpty')}</p>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>{t('common.employee')}</TableHead>
                        <TableHead className="text-right">{t('pay.th.confirmedDays')}</TableHead>
                        <TableHead className="text-right">{t('pay.th.regular')}</TableHead>
                        <TableHead className="text-right">{t('pay.th.ot')}</TableHead>
                        <TableHead className="text-right">{t('pay.th.holiday')}</TableHead>
                        <TableHead className="text-right">{t('pay.th.lateOffset')}</TableHead>
                        <TableHead className="text-right">{t('pay.th.base')}</TableHead>
                        <TableHead className="text-right">{t('pay.th.allowance')}</TableHead>
                        <TableHead className="text-right">{t('pay.th.deduction')}</TableHead>
                        <TableHead className="text-right">{t('pay.th.net')}</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {currentItems.map((i) => (
                        <TableRow key={i.id}>
                          <TableCell>
                            <div className="font-medium">{i.employee_name}</div>
                            <div className="text-xs text-muted-foreground">
                              {i.emp_no} · {i.department}
                            </div>
                          </TableCell>
                          <TableCell className="num text-right text-sm">
                            {i.confirmed_days ?? 0}/{fmtDays(i.work_days ?? 0)}
                          </TableCell>
                          <TableCell className="num text-right text-sm">{fmtMinutes(i.regular_minutes)}</TableCell>
                          <TableCell className="num text-right text-sm">{fmtMinutes(i.overtime_minutes)}</TableCell>
                          <TableCell className="num text-right text-sm">{fmtMinutes(i.holiday_minutes)}</TableCell>
                          <TableCell className="num text-right text-sm">
                            {(i.late_minutes ?? 0) > 0 ? (
                              <span className="text-destructive">{fmtMinutes(i.late_minutes)}</span>
                            ) : (
                              '—'
                            )}
                            {(i.offset_minutes ?? 0) > 0 ? (
                              <span className="ml-1 text-primary">(-{fmtMinutes(i.offset_minutes)})</span>
                            ) : null}
                          </TableCell>
                          <TableCell className="num text-right text-sm">{fmtMoney(i.base_pay)}</TableCell>
                          <TableCell className="num text-right text-sm">
                            {fmtMoney((i.overtime_pay ?? 0) + (i.holiday_pay ?? 0) + (i.night_pay ?? 0))}
                          </TableCell>
                          <TableCell className="num text-right text-sm text-destructive">
                            {fmtMoney((i.late_deduction ?? 0) + (i.absent_deduction ?? 0))}
                          </TableCell>
                          <TableCell className="num text-right font-semibold">{fmtMoney(i.net_pay)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </>
        ) : null}
      </div>
    </AppShell>
  );
}