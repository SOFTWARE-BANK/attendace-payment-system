import { useCallback, useEffect, useMemo, useState } from 'react';
import { CheckCircle2, FileCheck2, Loader2, RefreshCw, XCircle } from 'lucide-react';
import { toast } from 'sonner';
import AppShell from '@/components/AppShell';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Approval, DOC_TYPE_KEY, STEP_KEY, apiError, callApi, queryAll } from '@/lib/api';
import { useSession } from '@/hooks/useSession';
import { TransKey, useI18n } from '@/lib/i18n';

const STEPS = ['hr', 'manager', 'ceo'] as const;

function StepTracker({ doc }: { doc: Approval }) {
  const { t } = useI18n();
  const done: Record<string, boolean> = {
    hr: Boolean(doc.hr_approved_at),
    manager: Boolean(doc.manager_approved_at),
    ceo: Boolean(doc.ceo_approved_at),
  };
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {STEPS.map((step, idx) => {
        const isDone = done[step];
        const isCurrent = doc.current_step === step && doc.status === 'pending';
        return (
          <div key={step} className="flex items-center gap-1.5">
            <span
              className={
                isDone
                  ? 'rounded-md bg-primary px-2 py-0.5 text-[11px] font-medium text-primary-foreground'
                  : isCurrent
                    ? 'rounded-md border border-primary px-2 py-0.5 text-[11px] font-medium text-primary'
                    : 'rounded-md bg-muted px-2 py-0.5 text-[11px] text-muted-foreground'
              }
            >
              {t(STEP_KEY[step] as TransKey)}
              {isDone ? ' ✓' : isCurrent ? ` ${t('step.waiting')}` : ''}
            </span>
            {idx < STEPS.length - 1 ? <span className="text-muted-foreground">›</span> : null}
          </div>
        );
      })}
    </div>
  );
}

export default function ApprovalsPage() {
  const { actor } = useSession();
  const { t } = useI18n();
  const [docs, setDocs] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('mine');
  const [busy, setBusy] = useState(0);
  const [rejectTarget, setRejectTarget] = useState<Approval | null>(null);
  const [rejectReason, setRejectReason] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const rows = await queryAll<Approval>('approvals', { sort: '-id', limit: 300 });
      setDocs(rows);
    } catch (e) {
      toast.error(apiError(e, t('appr.loadFail')));
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const myStep = useMemo(() => {
    const role = actor?.role ?? 'employee';
    return { hr: 'hr', manager: 'manager', ceo: 'ceo' }[role] ?? '';
  }, [actor]);

  const filtered = useMemo(() => {
    if (tab === 'mine') return docs.filter((d) => d.status === 'pending' && d.current_step === myStep);
    if (tab === 'pending') return docs.filter((d) => d.status === 'pending');
    if (tab === 'approved') return docs.filter((d) => d.status === 'approved');
    if (tab === 'rejected') return docs.filter((d) => d.status === 'rejected');
    return docs;
  }, [docs, tab, myStep]);

  const canAct = (doc: Approval) => {
    if (!actor || doc.status !== 'pending') return false;
    const role = actor.role ?? 'employee';
    if (role === 'ceo') return true;
    return doc.current_step === role;
  };

  const approve = async (doc: Approval) => {
    if (!actor) return;
    setBusy(doc.id);
    try {
      const result = await callApi<{ current_step: string; current_step_label: string; applied?: { message?: string } }>(
        '/api/v1/attendance/approval/approve',
        'POST',
        { approval_id: doc.id, actor_emp_no: actor.emp_no, comment: '' },
      );
      const stepKey = STEP_KEY[result.current_step as keyof typeof STEP_KEY];
      toast.success(t('appr.approveOk'), {
        description: result.applied?.message
          ? result.applied.message
          : t('appr.nextStep', { step: stepKey ? t(stepKey as TransKey) : result.current_step_label }),
      });
      await load();
    } catch (e) {
      toast.error(apiError(e, t('appr.approveFail')));
    } finally {
      setBusy(0);
    }
  };

  const doReject = async () => {
    if (!rejectTarget || !actor) return;
    if (!rejectReason.trim()) {
      toast.error(t('appr.needReason'));
      return;
    }
    setBusy(rejectTarget.id);
    try {
      await callApi('/api/v1/attendance/approval/reject', 'POST', {
        approval_id: rejectTarget.id,
        actor_emp_no: actor.emp_no,
        reason: rejectReason,
      });
      toast.success(t('appr.rejectOk'), { description: t('appr.rejectOkDesc') });
      setRejectTarget(null);
      setRejectReason('');
      await load();
    } catch (e) {
      toast.error(apiError(e, t('appr.rejectFail')));
    } finally {
      setBusy(0);
    }
  };

  const counts = useMemo(
    () => ({
      mine: docs.filter((d) => d.status === 'pending' && d.current_step === myStep).length,
      pending: docs.filter((d) => d.status === 'pending').length,
      approved: docs.filter((d) => d.status === 'approved').length,
      rejected: docs.filter((d) => d.status === 'rejected').length,
    }),
    [docs, myStep],
  );

  return (
    <AppShell
      title={t('nav.approvals')}
      description={t('appr.desc')}
      actions={
        <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
          <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          {t('common.refresh')}
        </Button>
      }
    >
      <div className="space-y-6">
        <Card>
          <CardContent className="pt-6">
            <Tabs value={tab} onValueChange={setTab}>
              <TabsList>
                <TabsTrigger value="mine">{t('appr.tab.mine', { n: counts.mine })}</TabsTrigger>
                <TabsTrigger value="pending">{t('appr.tab.pending', { n: counts.pending })}</TabsTrigger>
                <TabsTrigger value="approved">{t('appr.tab.approved', { n: counts.approved })}</TabsTrigger>
                <TabsTrigger value="rejected">{t('appr.tab.rejected', { n: counts.rejected })}</TabsTrigger>
              </TabsList>
            </Tabs>
            <p className="mt-3 text-xs text-muted-foreground">
              {t('appr.actorLine')}:{' '}
              <span className="font-medium text-foreground">{actor?.name ?? t('common.notSelected')}</span> (
              {myStep ? t(STEP_KEY[myStep as keyof typeof STEP_KEY] as TransKey) : t('step.none')}) —{' '}
              {t('appr.actorHint')}
            </p>
          </CardContent>
        </Card>

        {loading ? (
          <div className="space-y-3">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-32 w-full" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center gap-2 py-14 text-center">
              <FileCheck2 className="h-8 w-8 text-muted-foreground" />
              <p className="font-medium">{t('appr.emptyTitle')}</p>
              <p className="text-sm text-muted-foreground">{t('appr.emptyDesc')}</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {filtered.map((doc) => (
              <Card key={doc.id}>
                <CardHeader className="pb-3">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="outline">
                          {DOC_TYPE_KEY[doc.doc_type as keyof typeof DOC_TYPE_KEY]
                            ? t(DOC_TYPE_KEY[doc.doc_type as keyof typeof DOC_TYPE_KEY] as TransKey)
                            : doc.doc_type}
                        </Badge>
                        <span className="num text-xs text-muted-foreground">{doc.doc_no}</span>
                        {doc.status === 'approved' ? (
                          <Badge className="bg-primary">{t('badge.approvedFinal')}</Badge>
                        ) : doc.status === 'rejected' ? (
                          <Badge variant="destructive">{t('badge.rejected')}</Badge>
                        ) : (
                          <Badge variant="secondary">
                            {t(
                              (STEP_KEY[(doc.current_step ?? 'hr') as keyof typeof STEP_KEY] ?? 'step.hr') as TransKey,
                            )}{' '}
                            {t('badge.waitingSuffix')}
                          </Badge>
                        )}
                      </div>
                      <CardTitle className="mt-2 text-base">{doc.title}</CardTitle>
                      <CardDescription className="mt-1">{doc.summary}</CardDescription>
                    </div>
                    {canAct(doc) ? (
                      <div className="flex shrink-0 gap-2">
                        <Button size="sm" onClick={() => void approve(doc)} disabled={busy === doc.id}>
                          {busy === doc.id ? (
                            <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                          ) : (
                            <CheckCircle2 className="mr-1.5 h-3.5 w-3.5" />
                          )}
                          {t('appr.approve')}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            setRejectTarget(doc);
                            setRejectReason('');
                          }}
                          disabled={busy === doc.id}
                        >
                          <XCircle className="mr-1.5 h-3.5 w-3.5" />
                          {t('appr.reject')}
                        </Button>
                      </div>
                    ) : null}
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <StepTracker doc={doc} />
                  <div className="grid gap-2 text-xs text-muted-foreground sm:grid-cols-3">
                    <div>
                      <span className="font-medium text-foreground">{t('step.hr')}</span>
                      <div>{doc.hr_approver ?? '—'}</div>
                      <div>{doc.hr_approved_at ? doc.hr_approved_at.replace('T', ' ').slice(0, 16) : ''}</div>
                    </div>
                    <div>
                      <span className="font-medium text-foreground">{t('step.manager')}</span>
                      <div>{doc.manager_approver ?? '—'}</div>
                      <div>{doc.manager_approved_at ? doc.manager_approved_at.replace('T', ' ').slice(0, 16) : ''}</div>
                    </div>
                    <div>
                      <span className="font-medium text-foreground">{t('step.ceo')}</span>
                      <div>{doc.ceo_approver ?? '—'}</div>
                      <div>{doc.ceo_approved_at ? doc.ceo_approved_at.replace('T', ' ').slice(0, 16) : ''}</div>
                    </div>
                  </div>
                  {doc.reject_reason ? (
                    <p className="rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive">
                      {t('appr.rejectedBy', { who: doc.rejected_by ?? '', reason: doc.reject_reason })}
                    </p>
                  ) : null}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      <Dialog open={rejectTarget !== null} onOpenChange={(open) => !open && setRejectTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('appr.dlg.title')}</DialogTitle>
            <DialogDescription>{rejectTarget?.title}</DialogDescription>
          </DialogHeader>
          <div className="space-y-1.5">
            <Label htmlFor="rr" className="text-xs">
              {t('appr.dlg.reasonLabel')}
            </Label>
            <Textarea
              id="rr"
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              rows={4}
              placeholder={t('appr.dlg.reasonPlaceholder')}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRejectTarget(null)}>
              {t('common.cancel')}
            </Button>
            <Button variant="destructive" onClick={() => void doReject()} disabled={busy === rejectTarget?.id}>
              {t('appr.dlg.submit')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}