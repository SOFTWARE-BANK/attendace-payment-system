import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  CalendarCheck2,
  Clock,
  Database,
  Loader2,
  RefreshCw,
  Search,
  Timer,
  Users,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import AppShell from '@/components/AppShell';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { DashboardData, apiError, callApi, shiftDays, todayISO } from '@/lib/api';
import { useI18n } from '@/lib/i18n';

const STATUS_COLORS: Record<string, string> = {
  normal: 'hsl(187 62% 34%)',
  late: 'hsl(28 84% 52%)',
  early_leave: 'hsl(45 82% 50%)',
  absent: 'hsl(0 72% 51%)',
  leave: 'hsl(215 60% 55%)',
  holiday_work: 'hsl(265 55% 58%)',
  business_trip: 'hsl(200 12% 55%)',
};

export default function Index() {
  const { t, lang, fmtMinutes, fmtCount, fmtTimes } = useI18n();
  const [start, setStart] = useState(() => shiftDays(todayISO(), -13));
  const [end, setEnd] = useState(() => todayISO());
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);

  const load = useCallback(
    async (from: string, to: string) => {
      setLoading(true);
      try {
        const result = await callApi<DashboardData>('/api/v1/attendance/dashboard', 'POST', {
          period_start: from,
          period_end: to,
        });
        setData(result);
      } catch (e) {
        toast.error(apiError(e, t('dash.loadError')));
      } finally {
        setLoading(false);
      }
    },
    [t],
  );

  useEffect(() => {
    void load(start, end);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const bootstrap = async () => {
    setSeeding(true);
    try {
      const spanDays =
        Math.floor((new Date(end).getTime() - new Date(start).getTime()) / 86400000) + 1;
      const seeded = await callApi<{ inserted: number }>('/api/v1/attendance/seed_demo_logs', 'POST', {
        days: Math.max(1, spanDays),
      });
      const settled = await callApi<{ created: number; updated: number }>(
        '/api/v1/attendance/settle_range',
        'POST',
        { period_start: start, period_end: end },
      );
      toast.success(t('dash.seedOk'), {
        description: t('dash.seedOkDesc', {
          a: fmtCount(seeded.inserted),
          b: fmtCount(settled.created + settled.updated),
        }),
      });
      await load(start, end);
    } catch (e) {
      toast.error(apiError(e, t('dash.seedFail')));
    } finally {
      setSeeding(false);
    }
  };

  const summary = data?.summary;
  const hasData = (summary?.total_records ?? 0) > 0;

  const trendData = useMemo(
    () =>
      (data?.trend ?? []).map((d) => ({
        date: d.date.slice(5),
        [t('status.normal')]: d.normal,
        [t('status.late')]: d.late,
        [t('status.absent')]: d.absent,
        [t('dash.th.ot')]: Math.round((d.overtime_minutes / 60) * 10) / 10,
      })),
    [data, t],
  );

  const pieData = useMemo(
    () =>
      (['normal', 'late', 'early_leave', 'absent', 'leave', 'holiday_work'] as const)
        .map((code) => ({
          name: t(`status.${code}` as 'status.normal'),
          value: summary?.[code] ?? 0,
          code,
        }))
        .filter((item) => item.value > 0),
    [summary, t],
  );

  const deptChart = useMemo(
    () =>
      (data?.by_department ?? []).map((d) => ({
        name: d.department,
        [t('dash.th.rate')]: d.attendance_rate,
        [t('dash.th.ot')]: Math.round((d.overtime_minutes / 60) * 10) / 10,
      })),
    [data, t],
  );

  return (
    <AppShell
      title={t('nav.dashboard')}
      description={t('dash.desc')}
      actions={
        <Button variant="outline" size="sm" onClick={() => void load(start, end)} disabled={loading}>
          <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          {t('common.refresh')}
        </Button>
      }
    >
      <div className="space-y-6">
        <Card>
          <CardContent className="flex flex-wrap items-end gap-4 pt-6">
            <div className="space-y-1.5">
              <Label htmlFor="df" className="text-xs">
                {t('dash.from')}
              </Label>
              <Input id="df" type="date" value={start} onChange={(e) => setStart(e.target.value)} className="w-40" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="dt" className="text-xs">
                {t('dash.to')}
              </Label>
              <Input id="dt" type="date" value={end} onChange={(e) => setEnd(e.target.value)} className="w-40" />
            </div>
            <Button onClick={() => void load(start, end)} disabled={loading}>
              <Search className="mr-1.5 h-4 w-4" />
              {t('dash.query')}
            </Button>
            <Button variant="secondary" onClick={() => void bootstrap()} disabled={seeding}>
              {seeding ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : <Database className="mr-1.5 h-4 w-4" />}
              {t('dash.bootstrap')}
            </Button>
          </CardContent>
        </Card>

        {loading ? (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-28 w-full" />
            ))}
          </div>
        ) : !hasData ? (
          <Card>
            <CardContent className="py-16 text-center">
              <CalendarCheck2 className="mx-auto h-10 w-10 text-muted-foreground" />
              <p className="mt-3 text-base font-semibold">{t('dash.emptyTitle')}</p>
              <p className="mx-auto mt-1.5 max-w-md text-sm text-muted-foreground">{t('dash.emptyDesc')}</p>
              <Button className="mt-5" onClick={() => void bootstrap()} disabled={seeding}>
                {seeding ? (
                  <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                ) : (
                  <Database className="mr-1.5 h-4 w-4" />
                )}
                {t('dash.emptyBtn')}
              </Button>
            </CardContent>
          </Card>
        ) : (
          <>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {[
                {
                  label: t('dash.kpi.records'),
                  value: fmtCount(summary?.total_records ?? 0),
                  hint: t('dash.kpi.recordsHint', {
                    a: fmtCount(summary?.confirmed ?? 0),
                    b: fmtCount(summary?.pending_approvals ?? 0),
                  }),
                  icon: Users,
                },
                {
                  label: t('dash.kpi.late'),
                  value: fmtTimes(summary?.late ?? 0),
                  hint: t('dash.kpi.lateHint', {
                    a: fmtMinutes(summary?.late_minutes ?? 0),
                    b: fmtMinutes(summary?.offset_minutes ?? 0),
                  }),
                  icon: Clock,
                },
                {
                  label: t('dash.kpi.otHoliday'),
                  value: fmtMinutes((summary?.overtime_minutes ?? 0) + (summary?.holiday_minutes ?? 0)),
                  hint: t('dash.kpi.otHolidayHint', {
                    a: fmtMinutes(summary?.overtime_minutes ?? 0),
                    b: fmtMinutes(summary?.holiday_minutes ?? 0),
                  }),
                  icon: Timer,
                },
                {
                  label: t('dash.kpi.absLeave'),
                  value: `${summary?.absent ?? 0} / ${summary?.leave ?? 0}`,
                  hint: t('dash.kpi.absLeaveHint'),
                  icon: AlertTriangle,
                },
              ].map((kpi) => {
                const Icon = kpi.icon;
                return (
                  <Card key={kpi.label}>
                    <CardContent className="pt-6">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                          {kpi.label}
                        </p>
                        <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
                      </div>
                      <p className="num mt-2 text-2xl font-bold tracking-tight">{kpi.value}</p>
                      <p className="mt-1 text-xs text-muted-foreground">{kpi.hint}</p>
                    </CardContent>
                  </Card>
                );
              })}
            </div>

            <div className="grid gap-6 lg:grid-cols-3">
              <Card className="lg:col-span-2">
                <CardHeader>
                  <CardTitle className="text-base">{t('dash.trendTitle')}</CardTitle>
                  <CardDescription>{t('dash.trendDesc')}</CardDescription>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={280}>
                    <LineChart data={trendData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(200 16% 90%)" />
                      <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                      <Legend wrapperStyle={{ fontSize: 12 }} />
                      <Line
                        type="monotone"
                        dataKey={t('status.normal')}
                        stroke={STATUS_COLORS.normal}
                        strokeWidth={2}
                        dot={false}
                      />
                      <Line
                        type="monotone"
                        dataKey={t('status.late')}
                        stroke={STATUS_COLORS.late}
                        strokeWidth={2}
                        dot={false}
                      />
                      <Line
                        type="monotone"
                        dataKey={t('status.absent')}
                        stroke={STATUS_COLORS.absent}
                        strokeWidth={2}
                        dot={false}
                      />
                      <Line
                        type="monotone"
                        dataKey={t('dash.th.ot')}
                        stroke={STATUS_COLORS.holiday_work}
                        strokeWidth={2}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">{t('dash.pieTitle')}</CardTitle>
                  <CardDescription>{t('dash.pieDesc')}</CardDescription>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={280}>
                    <PieChart>
                      <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90} paddingAngle={2}>
                        {pieData.map((entry) => (
                          <Cell key={entry.code} fill={STATUS_COLORS[entry.code] ?? 'hsl(200 12% 60%)'} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                      <Legend wrapperStyle={{ fontSize: 12 }} />
                    </PieChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">{t('dash.deptTitle')}</CardTitle>
                <CardDescription>{t('dash.deptDesc')}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={deptChart}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(200 16% 90%)" />
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Bar dataKey={t('dash.th.rate')} fill={STATUS_COLORS.normal} radius={[4, 4, 0, 0]} />
                    <Bar dataKey={t('dash.th.ot')} fill={STATUS_COLORS.holiday_work} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>

                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>{t('common.department')}</TableHead>
                        <TableHead className="text-right">{t('dash.th.records')}</TableHead>
                        <TableHead className="text-right">{t('status.late')}</TableHead>
                        <TableHead className="text-right">{t('status.absent')}</TableHead>
                        <TableHead className="text-right">{t('dash.th.overtime')}</TableHead>
                        <TableHead className="w-44">{t('dash.th.rate')}</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {(data?.by_department ?? []).map((d) => (
                        <TableRow key={d.department}>
                          <TableCell className="font-medium">{d.department}</TableCell>
                          <TableCell className="num text-right">{d.records}</TableCell>
                          <TableCell className="num text-right">{d.late}</TableCell>
                          <TableCell className="num text-right">{d.absent}</TableCell>
                          <TableCell className="num text-right">{fmtMinutes(d.overtime_minutes)}</TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Progress value={d.attendance_rate} className="h-2" />
                              <span className="num w-12 shrink-0 text-right text-xs font-medium">
                                {d.attendance_rate}%
                              </span>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">{t('dash.empTitle')}</CardTitle>
                <CardDescription>{t('dash.empDesc')}</CardDescription>
              </CardHeader>
              <CardContent className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t('common.employee')}</TableHead>
                      <TableHead className="text-right">{t('dash.th.records')}</TableHead>
                      <TableHead className="text-right">{t('dash.th.work')}</TableHead>
                      <TableHead className="text-right">{t('status.late')}</TableHead>
                      <TableHead className="text-right">{t('dash.th.offset')}</TableHead>
                      <TableHead className="text-right">{t('dash.th.ot')}</TableHead>
                      <TableHead className="text-right">{t('dash.th.holiday')}</TableHead>
                      <TableHead className="text-right">{t('dash.th.absLeave')}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(data?.by_employee ?? []).map((e) => (
                      <TableRow key={e.emp_no}>
                        <TableCell>
                          <div className="font-medium">{e.employee_name}</div>
                          <div className="text-xs text-muted-foreground">
                            {e.emp_no} · {e.department}
                          </div>
                        </TableCell>
                        <TableCell className="num text-right">{e.records}</TableCell>
                        <TableCell className="num text-right text-sm">{fmtMinutes(e.work_minutes)}</TableCell>
                        <TableCell className="num text-right text-sm">
                          {(e.late_minutes ?? 0) > 0 ? (
                            <span className="text-destructive">{fmtMinutes(e.late_minutes)}</span>
                          ) : (
                            '—'
                          )}
                        </TableCell>
                        <TableCell className="num text-right text-sm text-primary">
                          {(e.offset_minutes ?? 0) > 0 ? fmtMinutes(e.offset_minutes) : '—'}
                        </TableCell>
                        <TableCell className="num text-right text-sm">{fmtMinutes(e.overtime_minutes)}</TableCell>
                        <TableCell className="num text-right text-sm">{fmtMinutes(e.holiday_minutes)}</TableCell>
                        <TableCell className="num text-right text-sm">
                          {e.absent_days} / {e.leave_days}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                <p className="mt-4 text-xs text-muted-foreground">
                  {t('dash.footer', {
                    a: fmtCount(summary?.confirmed ?? 0),
                    b: fmtCount(summary?.pending_approvals ?? 0),
                  })}
                </p>
                <Badge variant="outline" className="mt-3 text-[11px]">
                  {lang === 'ko' ? '표시 언어: 한국어' : 'Idioma: Español'}
                </Badge>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </AppShell>
  );
}