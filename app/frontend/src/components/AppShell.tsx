import { ReactNode, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  CalendarClock,
  FileCheck2,
  LayoutDashboard,
  Menu,
  Plane,
  ScanFace,
  Settings2,
  Timer,
  Wallet,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useSession } from '@/hooks/useSession';
import { LANG_OPTIONS, Lang, TransKey, useI18n } from '@/lib/i18n';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';

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
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-gradient-to-br from-background via-background to-muted/30">
      {/* Desktop Sidebar */}
      <aside className="hidden w-64 shrink-0 flex-col border-r border-border/50 bg-sidebar/80 backdrop-blur-sm lg:flex">
        <div className="flex h-16 items-center gap-3 border-b border-border/50 px-5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-primary/80 text-primary-foreground shadow-lg shadow-primary/20">
            <ScanFace className="h-5 w-5" />
          </div>
          <div className="min-w-0 leading-tight">
            <p className="text-sm font-bold text-sidebar-foreground">{t('app.name')}</p>
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
                  'nav-item',
                  active ? 'nav-item-active' : 'nav-item-inactive',
                )}
              >
                <Icon className={cn('h-4 w-4 shrink-0', active && 'animate-scale-in')} />
                <span className="truncate">{t(item.key)}</span>
              </Link>
            );
          })}
        </nav>
        <div className="space-y-3 border-t border-border/50 p-4">
          <div>
            <p className="mb-2 px-1 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              {t('shell.roleSwitch')}
            </p>
            <Select value={actor?.emp_no ?? ''} onValueChange={setActorEmpNo}>
              <SelectTrigger className="h-9 text-xs bg-background/50">
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
            <p className="mb-2 px-1 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              {t('shell.language')}
            </p>
            <Select value={lang} onValueChange={(v) => setLang(v as Lang)}>
              <SelectTrigger className="h-9 text-xs bg-background/50">
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

      {/* Mobile Menu Overlay */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setMobileMenuOpen(false)} />
          <aside className="fixed inset-y-0 left-0 w-72 bg-sidebar shadow-2xl animate-slide-up">
            <div className="flex h-16 items-center justify-between border-b border-border/50 px-5">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-primary/80 text-primary-foreground shadow-lg">
                  <ScanFace className="h-5 w-5" />
                </div>
                <p className="text-sm font-bold">{t('app.name')}</p>
              </div>
              <Button variant="ghost" size="icon" onClick={() => setMobileMenuOpen(false)}>
                <X className="h-5 w-5" />
              </Button>
            </div>
            <nav className="flex flex-col gap-1 p-3">
              {NAV.map((item) => {
                const active = location.pathname === item.to;
                const Icon = item.icon;
                return (
                  <Link
                    key={item.to}
                    to={item.to}
                    onClick={() => setMobileMenuOpen(false)}
                    className={cn(
                      'nav-item',
                      active ? 'nav-item-active' : 'nav-item-inactive',
                    )}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    <span>{t(item.key)}</span>
                  </Link>
                );
              })}
            </nav>
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-10 flex h-16 items-center justify-between gap-4 border-b border-border/50 bg-background/80 px-4 backdrop-blur-md lg:px-8">
          <div className="flex items-center gap-3 min-w-0">
            <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setMobileMenuOpen(true)}>
              <Menu className="h-5 w-5" />
            </Button>
            <div className="min-w-0">
              <h1 className="truncate text-lg font-bold tracking-tight">{title}</h1>
              {description ? <p className="truncate text-xs text-muted-foreground">{description}</p> : null}
            </div>
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
              <Badge variant="secondary" className="hidden gap-1.5 px-3 py-1.5 sm:flex">
                <span className="font-medium">{actor.name}</span>
                <span className="text-muted-foreground">· {t(ROLE_KEY[actor.role ?? 'employee'])}</span>
              </Badge>
            ) : null}
          </div>
        </header>

        <nav className="flex gap-1 overflow-x-auto border-b border-border/50 px-3 py-2 lg:hidden">
          {NAV.map((item) => {
            const active = location.pathname === item.to;
            return (
              <Link
                key={item.to}
                to={item.to}
                className={cn(
                  'whitespace-nowrap rounded-lg px-3 py-1.5 text-xs font-medium transition-all',
                  active
                    ? 'bg-primary text-primary-foreground shadow-sm'
                    : 'text-muted-foreground hover:bg-accent',
                )}
              >
                {t(item.key)}
              </Link>
            );
          })}
        </nav>

        <main className="flex-1 p-4 lg:p-8 animate-fade-in">{children}</main>
      </div>
    </div>
  );
}
