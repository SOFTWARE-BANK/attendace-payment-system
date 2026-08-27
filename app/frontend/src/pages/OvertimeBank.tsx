import { useCallback, useEffect, useMemo, useState } from 'react';
import { ArrowRightLeft, Coins, Loader2, PiggyBank, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import AppShell from '@/components/AppShell';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { OvertimeBank as BankRow, TXN_KEY, apiError, callApi, queryAll, shiftDays, todayISO } from '@/lib/api';
import { useSession } from '@/hooks/useSession';
import { TransKey, useI18n } from '@/lib/i18n';

export default function OvertimeBankPage() {
  const { employees, actor } = useSession();
  const { t, fmtMinutes, fmtDays, fmtCount } = useI18n();
  const [rows, setRows] = useState<BankRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [earnDate, setEarnDate] = useState(() => shiftDays(todayISO(), -1));
  const [empNo, setEmpNo] = useState('');
  const [minutes, setMinutes] = useState('480');
  const [note, setNote] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await queryAll<BankRow>('overtime_banks', { sort: '-id', limit: 400 });
      setRows(data);
    } catch (e) {
      toast.error(apiError(e, t('ot.loadFail')));
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [actor]);

  const balances = useMemo(() => {
    const map = new Map<string, { emp_no: string; name?: string; dept?: string; earn: number; used: number; net: number }>();
    rows.forEach((r) => {
      if (r.status === 'rejected') return;
      const cur =
        map.get(r.emp_no) ?? { emp_no: r.emp_no, name: r.employee_name, dept: r.department, earn: 0, used: 0, net: 0 };
      const m = r.minutes ?? 0;
      if (m >= 0) cur.earn += m;
      else cur.used += Math.abs(m);
      cur.net += m;
      map.set(r.emp_no, cur);
    });
    return [...map.values()].sort((a, b) => b.net - a.net);
  }, [rows]);

  const selectedNet = balances.find((b) => b.emp_no === empNo)?.net ?? 0;

  const runEarn = async () => {
    setBusy('earn');
    try {
      const result = await callApi<{ earned_records: number }>('/api/v1/attendance/overtime/earn', 'POST', {
        work_date: earnDate,
      });
      if (result.earned_records === 0) {
        toast.info(t('ot.earnNone'), { description: t('ot.earnNoneDesc') });
      } else {
        toast.success(t('ot.earnOk', { n: fmtCount(result.earned_records) }));
      }
      await load();
    } catch (e) {
      toast.error(apiError(e, t('ot.earnFail')));
    } finally {
      setBusy('');
    }
  };

  const runConvert = async () => {
    if (!empNo) {
      toast.error(t('ot.needEmp'));
      return;
    }
    setBusy('convert');
    try {
      const result = await callApi<{ converted_days: number; doc_no: string }>(
        '/api/v1/attendance/overtime/convert',
        'POST',
        { emp_no: empNo, minutes: Number(minutes), note },
      );
      toast.success(t('ot.convertOk', { doc: result.doc_no }), {
        description: t('ot.convertOkDesc', {
          a: fmtMinutes(Number(minutes)),
          b: fmtDays(result.converted_days),
        }),
      });
      setNote('');
      await load();
    } catch (e) {
      toast.error(apiError(e, t('ot.convertFail')));
    } finally {
      setBusy('');
    }
  };

  return (
    <AppShell
      title={t('nav.overtime')}
      description={t('ot.desc')}
      actions={
        <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
          <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          {t('common.refresh')}
        </Button>
      }
    >
      <div className="space-y-6">
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t('ot.earnTitle')}</CardTitle>
              <CardDescription>{t('ot.earnDesc')}</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap items-end gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="ed" className="text-xs">
                  {t('ot.earnDate')}
                </Label>
                <Input id="ed" type="date" value={earnDate} onChange={(e) => setEarnDate(e.target.value)} className="w-40" />
              </div>
              <Button onClick={() => void runEarn()} disabled={busy === 'earn'}>
                {busy === 'earn' ? (
                  <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                ) : (
                  <PiggyBank className="mr-1.5 h-4 w-4" />
                )}
                {t('ot.earnBtn')}
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t('ot.convertTitle')}</CardTitle>
              <CardDescription>{t('ot.convertDesc')}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label className="text-xs">{t('common.employee')}</Label>
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
                  <Label htmlFor="cm" className="text-xs">
                    {t('ot.convertMinutes')}
                  </Label>
                  <Input id="cm" type="number" min={30} step={30} value={minutes} onChange={(e) => setMinutes(e.target.value)} />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="cn" className="text-xs">
                  {t('ot.convertReason')}
                </Label>
                <Textarea id="cn" value={note} onChange={(e) => setNote(e.target.value)} rows={2} />
              </div>
              <div className="rounded-md bg-muted px-3 py-2 text-xs">
                {t('ot.convertBalance', {
                  a: fmtMinutes(selectedNet),
                  b: fmtDays((selectedNet / 480).toFixed(2)),
                })}
              </div>
              <Button onClick={() => void runConvert()} disabled={busy === 'convert'} className="w-full">
                {busy === 'convert' ? (
                  <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                ) : (
                  <ArrowRightLeft className="mr-1.5 h-4 w-4" />
                )}
                {t('ot.convertBtn')}
              </Button>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t('ot.balanceTitle')}</CardTitle>
            <CardDescription>{t('ot.balanceDesc')}</CardDescription>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            {loading ? (
              <div className="space-y-2">
                {[0, 1, 2].map((i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            ) : balances.length === 0 ? (
              <div className="rounded-md border border-dashed border-border py-10 text-center">
                <Coins className="mx-auto h-7 w-7 text-muted-foreground" />
                <p className="mt-2 text-sm font-medium">{t('ot.balanceEmptyTitle')}</p>
                <p className="mt-1 text-xs text-muted-foreground">{t('ot.balanceEmptyHint')}</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t('common.employee')}</TableHead>
                    <TableHead>{t('common.department')}</TableHead>
                    <TableHead className="text-right">{t('ot.th.earned')}</TableHead>
                    <TableHead className="text-right">{t('ot.th.used')}</TableHead>
                    <TableHead className="text-right">{t('ot.th.net')}</TableHead>
                    <TableHead className="text-right">{t('ot.th.convertible')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {balances.map((b) => (
                    <TableRow key={b.emp_no}>
                      <TableCell className="font-medium">{b.name}</TableCell>
                      <TableCell className="text-sm">{b.dept}</TableCell>
                      <TableCell className="num text-right">{fmtMinutes(b.earn)}</TableCell>
                      <TableCell className="num text-right">{fmtMinutes(b.used)}</TableCell>
                      <TableCell className="num text-right font-medium text-primary">{fmtMinutes(b.net)}</TableCell>
                      <TableCell className="num text-right">{fmtDays((b.net / 480).toFixed(2))}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t('ot.txnTitle')}</CardTitle>
            <CardDescription>{t('ot.txnDesc')}</CardDescription>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            {loading ? (
              <div className="space-y-2">
                {[0, 1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            ) : rows.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">{t('ot.txnEmpty')}</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t('common.date')}</TableHead>
                    <TableHead>{t('common.employee')}</TableHead>
                    <TableHead>{t('common.type')}</TableHead>
                    <TableHead className="text-right">{t('ot.th.minutes')}</TableHead>
                    <TableHead className="text-right">{t('ot.th.convertDays')}</TableHead>
                    <TableHead>{t('common.status')}</TableHead>
                    <TableHead>{t('common.note')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell className="num text-sm">{r.txn_date ?? r.source_date ?? '—'}</TableCell>
                      <TableCell className="font-medium">{r.employee_name}</TableCell>
                      <TableCell>
                        <Badge variant={r.txn_type === 'earn' ? 'secondary' : 'outline'}>
                          {TXN_KEY[r.txn_type as keyof typeof TXN_KEY]
                            ? t(TXN_KEY[r.txn_type as keyof typeof TXN_KEY] as TransKey)
                            : r.txn_type}
                        </Badge>
                      </TableCell>
                      <TableCell className={`num text-right ${(r.minutes ?? 0) < 0 ? 'text-destructive' : 'text-primary'}`}>
                        {fmtMinutes(r.minutes)}
                      </TableCell>
                      <TableCell className="num text-right">
                        {r.target_leave_days ? fmtDays(r.target_leave_days) : '—'}
                      </TableCell>
                      <TableCell>
                        {r.status === 'approved' ? (
                          <Badge className="bg-primary">{t('badge.approved')}</Badge>
                        ) : r.status === 'rejected' ? (
                          <Badge variant="destructive">{t('badge.rejected')}</Badge>
                        ) : (
                          <Badge variant="secondary">{t('badge.inApproval')}</Badge>
                        )}
                      </TableCell>
                      <TableCell className="max-w-56 truncate text-xs text-muted-foreground">{r.note}</TableCell>
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