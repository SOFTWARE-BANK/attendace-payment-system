import { useCallback, useEffect, useState } from 'react';
import { Loader2, Plus, RefreshCw, Save, Trash2, Upload, ScanLine } from 'lucide-react';
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
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
  CATEGORY_KEY,
  CYCLE_KEY,
  Employee,
  PAY_EFFECT_KEY,
  ROLE_KEY,
  apiError,
  callApi,
  createEntity,
  deleteEntity,
  queryAll,
  updateEntity,
} from '@/lib/api';
import { useSession } from '@/hooks/useSession';
import { TransKey, useI18n } from '@/lib/i18n';

export default function MasterSettings() {
  const { reload } = useSession();
  const { t, fmtMoney } = useI18n();
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [reasons, setReasons] = useState<AttendanceReason[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [editEmp, setEditEmp] = useState<Employee | null>(null);
  const [newReason, setNewReason] = useState({
    code: '',
    name: '',
    category: 'late',
    pay_effect: 'deduct',
    deduct_rate: '1',
    offsettable: true,
    description: '',
  });

  const [syncing, setSyncing] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [emp, rsn] = await Promise.all([
        queryAll<Employee>('employees', { sort: 'emp_no', limit: 200 }),
        queryAll<AttendanceReason>('attendance_reasons', { sort: 'sort_order', limit: 100 }),
      ]);
      setEmployees(emp);
      setReasons(rsn);
    } catch (e) {
      toast.error(apiError(e, t('set.loadFail')));
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const syncFromReader = async () => {
    setSyncing(true);
    try {
      const result = await callApi<{ message: string; synced: number; created: number; total: number }>(
        '/api/v1/entities/employees/sync-from-reader',
        'POST'
      );
      toast.success(result.message || 'Sincronización completada');
      await load();
      await reload();
    } catch (e) {
      toast.error(apiError(e, 'Error al sincronizar'));
    } finally {
      setSyncing(false);
    }
  };

  useEffect(() => {
    void load();
  }, [load]);

  const saveEmployee = async () => {
    if (!editEmp) return;
    setBusy(true);
    try {
      await updateEntity('employees', editEmp.id, {
        department: editEmp.department,
        position: editEmp.position,
        role: editEmp.role,
        pay_type: editEmp.pay_type,
        hourly_rate: Number(editEmp.hourly_rate ?? 0),
        monthly_salary: Number(editEmp.monthly_salary ?? 0),
        pay_cycle: editEmp.pay_cycle,
        std_start: editEmp.std_start,
        std_end: editEmp.std_end,
        break_minutes: Number(editEmp.break_minutes ?? 60),
        grace_minutes: Number(editEmp.grace_minutes ?? 0),
        terminal_user_id: editEmp.terminal_user_id,
        manager_emp_no: editEmp.manager_emp_no,
      });
      toast.success(t('set.saveOk'));
      setEditEmp(null);
      await load();
      await reload();
    } catch (e) {
      toast.error(apiError(e, t('set.saveFail')));
    } finally {
      setBusy(false);
    }
  };

  const addReason = async () => {
    if (!newReason.code.trim() || !newReason.name.trim()) {
      toast.error(t('set.reasonNeedInput'));
      return;
    }
    setBusy(true);
    try {
      await createEntity('attendance_reasons', {
        code: newReason.code.trim().toUpperCase(),
        name: newReason.name.trim(),
        category: newReason.category,
        pay_effect: newReason.pay_effect,
        deduct_rate: Number(newReason.deduct_rate),
        requires_approval: true,
        offsettable: newReason.offsettable,
        sort_order: reasons.length + 1,
        description: newReason.description,
        active: true,
      });
      toast.success(t('set.reasonAddOk', { name: newReason.name }));
      setNewReason({
        code: '',
        name: '',
        category: 'late',
        pay_effect: 'deduct',
        deduct_rate: '1',
        offsettable: true,
        description: '',
      });
      await load();
    } catch (e) {
      toast.error(apiError(e, t('set.reasonAddFail')));
    } finally {
      setBusy(false);
    }
  };

  const toggleReason = async (r: AttendanceReason, active: boolean) => {
    try {
      await updateEntity('attendance_reasons', r.id, { active });
      setReasons((prev) => prev.map((x) => (x.id === r.id ? { ...x, active } : x)));
      toast.success(t('set.reasonToggleOk', { name: r.name, state: active ? t('set.reasonUse') : t('set.reasonUnuse') }));
    } catch (e) {
      toast.error(apiError(e, t('set.reasonToggleFail')));
    }
  };

  const removeReason = async (r: AttendanceReason) => {
    try {
      await deleteEntity('attendance_reasons', r.id);
      setReasons((prev) => prev.filter((x) => x.id !== r.id));
      toast.success(t('set.reasonDeleteOk', { name: r.name }));
    } catch (e) {
      toast.error(apiError(e, t('set.reasonDeleteFail')));
    }
  };

  const roleLabel = (role?: string | null) =>
    t((ROLE_KEY[(role ?? 'employee') as keyof typeof ROLE_KEY] ?? 'role.employee') as TransKey);
  const cycleLabel = (cycle?: string | null) =>
    t((CYCLE_KEY[(cycle ?? 'monthly') as keyof typeof CYCLE_KEY] ?? 'cycle.monthly') as TransKey);
  const categoryLabel = (cat?: string | null) =>
    t((CATEGORY_KEY[(cat ?? 'etc') as keyof typeof CATEGORY_KEY] ?? 'category.etc') as TransKey);
  const payEffectLabel = (effect?: string | null) =>
    t((PAY_EFFECT_KEY[(effect ?? 'paid') as keyof typeof PAY_EFFECT_KEY] ?? 'payEffect.paid') as TransKey);

  return (
    <AppShell
      title={t('nav.settings')}
      description={t('set.desc')}
      actions={
        <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
          <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          {t('common.refresh')}
        </Button>
      }
    >
      <Tabs defaultValue="employees" className="space-y-6">
        <TabsList>
          <TabsTrigger value="employees">{t('set.tab.employees')}</TabsTrigger>
          <TabsTrigger value="reasons">{t('set.tab.reasons')}</TabsTrigger>
        </TabsList>

        <TabsContent value="employees">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base">{t('set.empTitle')}</CardTitle>
                  <CardDescription>{t('set.empDesc')}</CardDescription>
                </div>
                <Button variant="outline" size="sm" onClick={() => void syncFromReader()} disabled={syncing}>
                  {syncing ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> : <ScanLine className="mr-1.5 h-3.5 w-3.5" />}
                  Sincronizar Lector
                </Button>
              </div>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              {loading ? (
                <div className="space-y-2">
                  {[0, 1, 2, 3].map((i) => (
                    <Skeleton key={i} className="h-11 w-full" />
                  ))}
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t('common.employee')}</TableHead>
                      <TableHead>{t('set.th.role')}</TableHead>
                      <TableHead>{t('set.th.stdWork')}</TableHead>
                      <TableHead className="text-right">{t('set.th.graceBreak')}</TableHead>
                      <TableHead>{t('set.th.pay')}</TableHead>
                      <TableHead>{t('set.th.cycle')}</TableHead>
                      <TableHead>{t('set.th.terminal')}</TableHead>
                      <TableHead className="text-right">{t('common.edit')}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {employees.map((e) => (
                      <TableRow key={e.id}>
                        <TableCell>
                          <div className="font-medium">{e.name}</div>
                          <div className="text-xs text-muted-foreground">
                            {e.emp_no} · {e.department} {e.position}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={e.role === 'ceo' ? 'default' : 'outline'}>{roleLabel(e.role)}</Badge>
                        </TableCell>
                        <TableCell className="num text-sm">
                          {e.std_start} ~ {e.std_end}
                        </TableCell>
                        <TableCell className="num text-right text-sm">
                          {e.grace_minutes ?? 0} / {e.break_minutes ?? 60}
                        </TableCell>
                        <TableCell className="num text-sm">
                          {e.pay_type === 'monthly'
                            ? t('set.payMonthly', { a: fmtMoney(e.monthly_salary ?? 0) })
                            : t('set.payHourly', { a: fmtMoney(e.hourly_rate ?? 0) })}
                        </TableCell>
                        <TableCell className="text-sm">{cycleLabel(e.pay_cycle)}</TableCell>
                        <TableCell className="num text-xs text-muted-foreground">{e.terminal_user_id}</TableCell>
                        <TableCell className="text-right">
                          <Button size="sm" variant="ghost" onClick={() => setEditEmp({ ...e })}>
                            {t('common.edit')}
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="reasons" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-5">
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle className="text-base">{t('set.reasonFormTitle')}</CardTitle>
                <CardDescription>{t('set.reasonFormDesc')}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="space-y-1.5">
                    <Label htmlFor="rc" className="text-xs">
                      {t('set.reasonCode')}
                    </Label>
                    <Input
                      id="rc"
                      value={newReason.code}
                      onChange={(e) => setNewReason({ ...newReason, code: e.target.value })}
                      placeholder="LATE_WEATHER"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="rn" className="text-xs">
                      {t('set.reasonName')}
                    </Label>
                    <Input
                      id="rn"
                      value={newReason.name}
                      onChange={(e) => setNewReason({ ...newReason, name: e.target.value })}
                      placeholder={t('set.reasonNamePlaceholder')}
                    />
                  </div>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="space-y-1.5">
                    <Label className="text-xs">{t('set.reasonCategory')}</Label>
                    <Select
                      value={newReason.category}
                      onValueChange={(v) => setNewReason({ ...newReason, category: v })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.keys(CATEGORY_KEY).map((k) => (
                          <SelectItem key={k} value={k}>
                            {categoryLabel(k)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs">{t('set.reasonPayEffect')}</Label>
                    <Select
                      value={newReason.pay_effect}
                      onValueChange={(v) => setNewReason({ ...newReason, pay_effect: v })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.keys(PAY_EFFECT_KEY).map((k) => (
                          <SelectItem key={k} value={k}>
                            {payEffectLabel(k)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="rd" className="text-xs">
                    {t('set.reasonDeductRate')}
                  </Label>
                  <Input
                    id="rd"
                    type="number"
                    step="0.1"
                    min="0"
                    max="1"
                    value={newReason.deduct_rate}
                    onChange={(e) => setNewReason({ ...newReason, deduct_rate: e.target.value })}
                  />
                </div>
                <div className="flex items-center gap-2">
                  <Switch
                    id="ro"
                    checked={newReason.offsettable}
                    onCheckedChange={(v) => setNewReason({ ...newReason, offsettable: v })}
                  />
                  <Label htmlFor="ro" className="text-xs">
                    {t('set.reasonOffsettable')}
                  </Label>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="rdesc" className="text-xs">
                    {t('set.reasonDescription')}
                  </Label>
                  <Input
                    id="rdesc"
                    value={newReason.description}
                    onChange={(e) => setNewReason({ ...newReason, description: e.target.value })}
                  />
                </div>
                <Button onClick={() => void addReason()} disabled={busy} className="w-full">
                  {busy ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : <Plus className="mr-1.5 h-4 w-4" />}
                  {t('set.reasonAddBtn')}
                </Button>
              </CardContent>
            </Card>

            <Card className="lg:col-span-3">
              <CardHeader>
                <CardTitle className="text-base">{t('set.reasonListTitle')}</CardTitle>
                <CardDescription>{t('set.reasonListDesc')}</CardDescription>
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
                        <TableHead>{t('set.th.code')}</TableHead>
                        <TableHead>{t('set.th.label')}</TableHead>
                        <TableHead>{t('set.th.category')}</TableHead>
                        <TableHead>{t('set.th.payEffect')}</TableHead>
                        <TableHead className="text-right">{t('set.th.deductRate')}</TableHead>
                        <TableHead>{t('set.th.offset')}</TableHead>
                        <TableHead>{t('set.th.use')}</TableHead>
                        <TableHead className="text-right">{t('set.th.delete')}</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {reasons.map((r) => (
                        <TableRow key={r.id}>
                          <TableCell className="num text-xs text-muted-foreground">{r.code}</TableCell>
                          <TableCell className="font-medium">{r.name}</TableCell>
                          <TableCell className="text-sm">{categoryLabel(r.category)}</TableCell>
                          <TableCell className="text-sm">{payEffectLabel(r.pay_effect)}</TableCell>
                          <TableCell className="num text-right text-sm">{r.deduct_rate ?? 0}</TableCell>
                          <TableCell>
                            {r.offsettable ? (
                              <Badge variant="secondary">{t('set.offsetAllowed')}</Badge>
                            ) : (
                              <span className="text-xs text-muted-foreground">—</span>
                            )}
                          </TableCell>
                          <TableCell>
                            <Switch checked={r.active !== false} onCheckedChange={(v) => void toggleReason(r, v)} />
                          </TableCell>
                          <TableCell className="text-right">
                            <Button size="sm" variant="ghost" onClick={() => void removeReason(r)}>
                              <Trash2 className="h-3.5 w-3.5 text-destructive" />
                            </Button>
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

      <Dialog open={editEmp !== null} onOpenChange={(open) => !open && setEditEmp(null)}>
        <DialogContent className="max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t('set.dlg.title', { name: editEmp?.name ?? '' })}</DialogTitle>
            <DialogDescription>{t('set.dlg.desc', { empNo: editEmp?.emp_no ?? '' })}</DialogDescription>
          </DialogHeader>
          {editEmp ? (
            <div className="space-y-3">
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label className="text-xs">{t('common.department')}</Label>
                  <Input
                    value={editEmp.department ?? ''}
                    onChange={(e) => setEditEmp({ ...editEmp, department: e.target.value })}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">{t('common.position')}</Label>
                  <Input
                    value={editEmp.position ?? ''}
                    onChange={(e) => setEditEmp({ ...editEmp, position: e.target.value })}
                  />
                </div>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label className="text-xs">{t('set.dlg.role')}</Label>
                  <Select value={editEmp.role ?? 'employee'} onValueChange={(v) => setEditEmp({ ...editEmp, role: v })}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.keys(ROLE_KEY).map((k) => (
                        <SelectItem key={k} value={k}>
                          {roleLabel(k)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">{t('set.dlg.managerEmpNo')}</Label>
                  <Input
                    value={editEmp.manager_emp_no ?? ''}
                    onChange={(e) => setEditEmp({ ...editEmp, manager_emp_no: e.target.value })}
                  />
                </div>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label className="text-xs">{t('set.dlg.stdStart')}</Label>
                  <Input
                    type="time"
                    value={editEmp.std_start ?? '09:00'}
                    onChange={(e) => setEditEmp({ ...editEmp, std_start: e.target.value })}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">{t('set.dlg.stdEnd')}</Label>
                  <Input
                    type="time"
                    value={editEmp.std_end ?? '18:00'}
                    onChange={(e) => setEditEmp({ ...editEmp, std_end: e.target.value })}
                  />
                </div>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label className="text-xs">{t('set.dlg.grace')}</Label>
                  <Input
                    type="number"
                    value={editEmp.grace_minutes ?? 0}
                    onChange={(e) => setEditEmp({ ...editEmp, grace_minutes: Number(e.target.value) })}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">{t('set.dlg.break')}</Label>
                  <Input
                    type="number"
                    value={editEmp.break_minutes ?? 60}
                    onChange={(e) => setEditEmp({ ...editEmp, break_minutes: Number(e.target.value) })}
                  />
                </div>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label className="text-xs">{t('set.dlg.payType')}</Label>
                  <Select
                    value={editEmp.pay_type ?? 'monthly'}
                    onValueChange={(v) => setEditEmp({ ...editEmp, pay_type: v })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="hourly">{t('set.dlg.payTypeHourly')}</SelectItem>
                      <SelectItem value="monthly">{t('set.dlg.payTypeMonthly')}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">{t('set.dlg.payCycle')}</Label>
                  <Select
                    value={editEmp.pay_cycle ?? 'monthly'}
                    onValueChange={(v) => setEditEmp({ ...editEmp, pay_cycle: v })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.keys(CYCLE_KEY).map((k) => (
                        <SelectItem key={k} value={k}>
                          {cycleLabel(k)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label className="text-xs">{t('set.dlg.hourlyRate')}</Label>
                  <Input
                    type="number"
                    value={editEmp.hourly_rate ?? 0}
                    onChange={(e) => setEditEmp({ ...editEmp, hourly_rate: Number(e.target.value) })}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">{t('set.dlg.monthlySalary')}</Label>
                  <Input
                    type="number"
                    value={editEmp.monthly_salary ?? 0}
                    onChange={(e) => setEditEmp({ ...editEmp, monthly_salary: Number(e.target.value) })}
                  />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">{t('set.dlg.terminalId')}</Label>
                <Input
                  value={editEmp.terminal_user_id ?? ''}
                  onChange={(e) => setEditEmp({ ...editEmp, terminal_user_id: e.target.value })}
                />
              </div>
            </div>
          ) : null}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditEmp(null)}>
              {t('common.cancel')}
            </Button>
            <Button onClick={() => void saveEmployee()} disabled={busy}>
              {busy ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : <Save className="mr-1.5 h-4 w-4" />}
              {t('common.save')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}