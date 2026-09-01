import { useCallback, useEffect, useMemo, useState } from 'react';
import { Loader2, RefreshCw, ScanFace, Upload } from 'lucide-react';
import { toast } from 'sonner';
import AppShell from '@/components/AppShell';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { AccessLog, apiError, callApi, fmtLocalDateTime, fmtLocalTime, localDateOf, queryAll, todayISO } from '@/lib/api';
import { useSession } from '@/hooks/useSession';
import { useI18n } from '@/lib/i18n';

const SAMPLE = `[
  { "employeeNo": "HK1004", "event_time": "2026-08-24T08:47:00", "event_type": "IN", "auth_mode": "face" },
  { "employeeNo": "HK1004", "event_time": "2026-08-24T18:31:00", "event_type": "OUT", "auth_mode": "face" }
]`;

export default function AccessLogs() {
  const { employees } = useSession();
  const { t, fmtCount } = useI18n();
  const [logs, setLogs] = useState<AccessLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [date, setDate] = useState(() => todayISO());
  const [empFilter, setEmpFilter] = useState('all');
  const [payload, setPayload] = useState(SAMPLE);
  const [importing, setImporting] = useState(false);
  const [settling, setSettling] = useState(false);
  const [syncing, setSyncing] = useState(false);

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const rows = await queryAll<AccessLog>('access_logs', { sort: '-event_time', limit: 500 });
      setLogs(rows);
    } catch (e) {
      if (!silent) toast.error(apiError(e, t('logs.loadFail')));
    } finally {
      if (!silent) setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // Auto-refresh: con el alertStream el backend sincroniza cada checada al
  // instante, así que la pantalla se reconsulta sola cada 5s (en silencio y
  // solo con la pestaña visible) y también al volver a enfocar la ventana.
  useEffect(() => {
    const tick = () => {
      if (document.visibilityState === 'visible') void load(true);
    };
    const id = window.setInterval(tick, 5000);
    const onVisible = () => {
      if (document.visibilityState === 'visible') void load(true);
    };
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      window.clearInterval(id);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [load]);

  const filtered = useMemo(
    () =>
      logs.filter((l) => {
        const matchDate = !date || localDateOf(l.event_time) === date;
        const matchEmp = empFilter === 'all' || l.emp_no === empFilter;
        return matchDate && matchEmp;
      }),
    [logs, date, empFilter],
  );

  const grouped = useMemo(() => {
    const map = new Map<string, { emp_no: string; name?: string; first?: string; last?: string; count: number }>();
    filtered.forEach((l) => {
      const cur = map.get(l.emp_no) ?? { emp_no: l.emp_no, name: l.employee_name, count: 0 };
      cur.count += 1;
      if (!cur.first || l.event_time < cur.first) cur.first = l.event_time;
      if (!cur.last || l.event_time > cur.last) cur.last = l.event_time;
      map.set(l.emp_no, cur);
    });
    return [...map.values()].sort((a, b) => a.emp_no.localeCompare(b.emp_no));
  }, [filtered]);

  const handleImport = async () => {
    let records: Record<string, unknown>[];
    try {
      const parsed = JSON.parse(payload);
      records = Array.isArray(parsed) ? parsed : [parsed];
    } catch {
      toast.error(t('logs.badJson'));
      return;
    }
    setImporting(true);
    try {
      const result = await callApi<{ inserted: number; skipped: number }>(
        '/api/v1/attendance/import_logs',
        'POST',
        { records, source: 'upload' },
      );
      toast.success(t('logs.importOk', { n: fmtCount(result.inserted) }), {
        description: result.skipped > 0 ? t('logs.importSkipped', { n: fmtCount(result.skipped) }) : undefined,
      });
      await load();
    } catch (e) {
      toast.error(apiError(e, t('logs.importFail')));
    } finally {
      setImporting(false);
    }
  };

  const handleSettle = async () => {
    setSettling(true);
    try {
      const result = await callApi<{ created: number; updated: number; logs_matched: number }>(
        '/api/v1/attendance/settle',
        'POST',
        { work_date: date },
      );
      toast.success(t('logs.settleOk'), {
        description: t('logs.settleOkDesc', {
          a: fmtCount(result.created),
          b: fmtCount(result.updated),
          c: fmtCount(result.logs_matched),
        }),
      });
    } catch (e) {
      toast.error(apiError(e, t('logs.settleFail')));
    } finally {
      setSettling(false);
    }
  };

  const handleHikvisionSync = async () => {
    setSyncing(true);
    try {
      const start = new Date(`${date}T00:00:00`).toISOString();
      const end = new Date(`${date}T23:59:59`).toISOString();
      const result = await callApi<{
        fetched: number;
        inserted: number;
        duplicates: number;
        skipped: number;
        provisioned?: string[];
        unmatched_employee_ids?: string[];
      }>(
        '/api/v1/attendance/hikvision/sync',
        'POST',
        { start_time: start, end_time: end },
      );
      toast.success(t('logs.syncOk'), {
        description: t('logs.syncOkDesc', {
          a: fmtCount(result.fetched),
          b: fmtCount(result.inserted),
          c: fmtCount(result.duplicates),
          d: fmtCount(result.skipped),
        }),
      });
      if (result.provisioned?.length) {
        toast.success(t('logs.provisioned', { n: result.provisioned.join(', ') }));
      }
      if (result.unmatched_employee_ids?.length) {
        toast.error(`IDs Hikvision sin mapear: ${result.unmatched_employee_ids.join(', ')}`);
      }
      await load();
    } catch (e) {
      toast.error(apiError(e, t('logs.syncFail')));
    } finally {
      setSyncing(false);
    }
  };

  return (
    <AppShell
      title={t('nav.logs')}
      description={t('logs.desc')}
      actions={
        <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
          <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          {t('common.refresh')}
        </Button>
      }
    >
      <div className="space-y-6">
        <div className="grid gap-6 lg:grid-cols-5">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="text-base">{t('logs.importTitle')}</CardTitle>
              <CardDescription>{t('logs.importDesc')}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-1.5">
                <Label htmlFor="payload" className="text-xs">
                  {t('logs.jsonLabel')}
                </Label>
                <Textarea
                  id="payload"
                  value={payload}
                  onChange={(e) => setPayload(e.target.value)}
                  rows={9}
                  className="font-mono text-xs"
                />
              </div>
              <p className="text-xs text-muted-foreground">{t('logs.keysHint')}</p>
              <Button onClick={() => void handleImport()} disabled={importing} className="w-full">
                {importing ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : <Upload className="mr-1.5 h-4 w-4" />}
                {t('logs.importBtn')}
              </Button>
            </CardContent>
          </Card>

          <Card className="lg:col-span-3">
            <CardHeader>
              <CardTitle className="text-base">{t('logs.extractTitle')}</CardTitle>
              <CardDescription>{t('logs.extractDesc')}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap items-end gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="logdate" className="text-xs">
                    {t('logs.dateLabel')}
                  </Label>
                  <Input id="logdate" type="date" value={date} onChange={(e) => setDate(e.target.value)} className="w-40" />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">{t('common.employee')}</Label>
                  <Select value={empFilter} onValueChange={setEmpFilter}>
                    <SelectTrigger className="w-44">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">{t('logs.allEmp')}</SelectItem>
                      {employees.map((e) => (
                        <SelectItem key={e.emp_no} value={e.emp_no}>
                          {e.name} ({e.emp_no})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <Button onClick={() => void handleSettle()} disabled={settling}>
                  {settling ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : null}
                  {t('logs.settleBtn')}
                </Button>
                <Button variant="secondary" onClick={() => void handleHikvisionSync()} disabled={syncing}>
                  {syncing ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : <ScanFace className="mr-1.5 h-4 w-4" />}
                  {t('logs.syncBtn')}
                </Button>
              </div>

              {grouped.length === 0 ? (
                <div className="rounded-md border border-dashed border-border py-10 text-center">
                  <ScanFace className="mx-auto h-7 w-7 text-muted-foreground" />
                  <p className="mt-2 text-sm font-medium">{t('logs.emptyDay')}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{t('logs.emptyDayHint')}</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t('common.empNo')}</TableHead>
                      <TableHead>{t('common.name')}</TableHead>
                      <TableHead>{t('logs.th.count')}</TableHead>
                      <TableHead>{t('logs.th.firstIn')}</TableHead>
                      <TableHead>{t('logs.th.lastOut')}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {grouped.map((g) => (
                      <TableRow key={g.emp_no}>
                        <TableCell className="num text-muted-foreground">{g.emp_no}</TableCell>
                        <TableCell className="font-medium">{g.name}</TableCell>
                        <TableCell className="num">{fmtCount(g.count)}</TableCell>
                        <TableCell className="num">{g.first ? fmtLocalTime(g.first) : '—'}</TableCell>
                        <TableCell className="num">{g.last ? fmtLocalTime(g.last) : '—'}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t('logs.rawTitle')}</CardTitle>
            <CardDescription>
              {loading
                ? t('common.loading')
                : t('logs.rawDesc', { a: fmtCount(filtered.length), b: fmtCount(logs.length) })}
            </CardDescription>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            {loading ? (
              <div className="space-y-2">
                {[0, 1, 2, 3, 4].map((i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t('logs.th.time')}</TableHead>
                    <TableHead>{t('common.empNo')}</TableHead>
                    <TableHead>{t('common.name')}</TableHead>
                    <TableHead>{t('logs.th.kind')}</TableHead>
                    <TableHead>{t('logs.th.auth')}</TableHead>
                    <TableHead>{t('logs.th.terminal')}</TableHead>
                    <TableHead>{t('logs.th.source')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.slice(0, 200).map((l) => (
                    <TableRow key={l.id}>
                      <TableCell className="num">{fmtLocalDateTime(l.event_time)}</TableCell>
                      <TableCell className="num text-muted-foreground">{l.emp_no}</TableCell>
                      <TableCell>{l.employee_name}</TableCell>
                      <TableCell>
                        <Badge variant={l.event_type === 'IN' ? 'default' : l.event_type === 'OUT' ? 'secondary' : 'outline'}>
                          {l.event_type === 'IN' ? t('logs.in') : l.event_type === 'OUT' ? t('logs.out') : t('logs.access')}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">{l.auth_mode}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">{l.terminal_id}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">{l.source}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}