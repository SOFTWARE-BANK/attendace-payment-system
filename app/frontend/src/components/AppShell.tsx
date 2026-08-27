import { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  CalendarClock,
  FileCheck2,
  LayoutDashboard,
  Plane,
  ScanFace,
  Settings2,
  Timer,
  Wallet,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useSession } from '@/hooks/useSession';
import { LANG_OPTIONS, Lang, TransKey, useI18n } from '@/lib/i18n';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

const NAV: Array<{ to: string; key: TransKey; icon: typeof LayoutDashboard }> = [
  { to: '/', key: 'nav.dashboard', icon: LayoutDashboard },
  { to: '/logs', key: 'nav.logs', icon: ScanFace },
  { to: '/daily', key: 'nav.daily', icon: CalendarClock },
  { to: '/approvals', key: 'nav.approvals', icon: FileCheck2 },
  { to: '/leave', key: 'nav.leave', icon: Plane },
  { to: '/overtime', key: 'nav.overtime', icon: Timer },
  { to: '/payroll', key: 'nav.payroll', icon: Wallet },
  { to: '/settings', key: 'nav.settings', icon: Settings2 },
];

const ROLE_KEY: Record<string, TransKey> = {
  ceo: 'role.ceo',
  manager: 'role.manager',
  hr: 'role.hr',
  employee: 'role.employee',
};

interface AppShellProps {
  children: ReactNode;
  title: string;
  description?: string;
  actions?: ReactNode;
}

export default function AppShell({ children, title, description, actions }: AppShellProps) {
  const location = useLocation();
  const { employees, actor, setActorEmpNo } = useSession();
  const { t, lang, setLang } = useI18n();

  return (
    <div className="flex min-h-screen bg-background">
      <aside className="hidden w-60 shrink-0 flex-col border-r border-border bg-sidebar lg:flex">
        <div className="flex h-16 items-center gap-2 border-b border-border px-5">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <ScanFace className="h-4 w-4" />
          </div>
          <div className="min-w-0 leading-tight">
            <p className="text-sm font-semibold text-sidebar-foreground">{t('app.name')}</p>
            <p className="truncate text-[11px] text-muted-foreground">{t('app.tagline')}</p>
          </div>
        </div>
        <nav className="flex flex-1 flex-col gap-1 p-3">
          {NAV.map((item) => {
            const active = location.pathname === item.to;
            const Icon = item.icon;
            return (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  'flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors duration-200',
                  active
                    ? 'bg-primary text-primary-foreground font-medium'
                    : 'text-sidebar-foreground hover:bg-accent hover:text-accent-foreground',
                )}
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span className="truncate">{t(item.key)}</span>
              </Link>
            );
          })}
        </nav>
        <div className="space-y-3 border-t border-border p-3">
          <div>
            <p className="mb-1.5 px-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
              {t('shell.roleSwitch')}
            </p>
            <Select value={actor?.emp_no ?? ''} onValueChange={setActorEmpNo}>
              <SelectTrigger className="h-9 text-xs">
                <SelectValue placeholder={t('shell.selectActor')} />
              </SelectTrigger>
              <SelectContent>
                {employees.map((e) => (
                  <SelectItem key={e.emp_no} value={e.emp_no} className="text-xs">
                    {e.name} · {e.department}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <p className="mb-1.5 px-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
              {t('shell.language')}
            </p>
            <Select value={lang} onValueChange={(v) => setLang(v as Lang)}>
              <SelectTrigger className="h-9 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {LANG_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value} className="text-xs">
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-10 flex h-16 items-center justify-between gap-4 border-b border-border bg-background/95 px-5 backdrop-blur lg:px-8">
          <div className="min-w-0">
            <h1 className="truncate text-lg font-semibold tracking-tight">{title}</h1>
            {description ? <p className="truncate text-xs text-muted-foreground">{description}</p> : null}
          </div>
          <div className="flex shrink-0 items-center gap-3">
            {actions}
            <Select value={lang} onValueChange={(v) => setLang(v as Lang)}>
              <SelectTrigger className="h-8 w-[104px] text-xs lg:hidden">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {LANG_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value} className="text-xs">
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {actor ? (
              <Badge variant="secondary" className="hidden gap-1.5 sm:flex">
                <span className="font-medium">{actor.name}</span>
                <span className="text-muted-foreground">{t(ROLE_KEY[actor.role ?? 'employee'])}</span>
              </Badge>
            ) : null}
          </div>
        </header>

        <nav className="flex gap-1 overflow-x-auto border-b border-border px-3 py-2 lg:hidden">
          {NAV.map((item) => {
            const active = location.pathname === item.to;
            return (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  'whitespace-nowrap rounded-md px-3 py-1.5 text-xs transition-colors',
                  active ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-accent',
                )}
              >
                {t(item.key)}
              </Link>
            );
          })}
        </nav>

        <main className="flex-1 p-5 lg:p-8">{children}</main>
      </div>
    </div>
  );
}