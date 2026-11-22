import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Link, useLocation, useNavigationType } from 'react-router-dom';
import {
  Bell,
  CalendarDays,
  ChartColumn,
  CircleQuestionMark,
  FileText,
  GraduationCap,
  House,
  Inbox,
  Info,
  LogOut,
  type LucideIcon,
  Megaphone,
  UserRound,
} from 'lucide-react';
import { useAuth } from '../../auth/AuthContext';
import { useUnreadCount } from '../../api/hooks';
import { Avatar } from '../ui/Avatar';
import { Logo, LogoMark } from '../ui/Logo';
import { plural } from '../../lib/format';

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  /** Пункт активен, если путь начинается с одного из префиксов */
  match: string[];
  badge?: number;
  end?: boolean;
}

function isActive(pathname: string, item: NavItem): boolean {
  if (item.end) return pathname === item.to;
  return item.match.some((m) => pathname === m || pathname.startsWith(`${m}/`));
}

const SECTION_TITLES: [string, string][] = [
  ['/staff/grades', 'Студенты и баллы'],
  ['/staff/announcements', 'Объявления'],
  ['/staff', 'Заявки'],
  ['/schedule', 'Расписание'],
  ['/study', 'Учёба'],
  ['/applications', 'Заявки'],
  ['/notifications', 'Уведомления'],
  ['/profile', 'Профиль'],
  ['/help', 'Помощь'],
];

function sectionTitle(pathname: string): string {
  if (pathname === '/') return 'Главная';
  return SECTION_TITLES.find(([p]) => pathname === p || pathname.startsWith(`${p}/`))?.[1] ?? 'Цифровой деканат';
}

export function DisclaimerBar() {
  return (
    <div className="disclaimer-bar no-print" role="note">
      <Info aria-hidden="true" />
      <span>
        Концепт для конкурса, не официальный сервис университета
        <span className="disclaimer-bar__extra"> · Данные вымышлены</span>
      </span>
    </div>
  );
}

function UserMenu({ compactOnMobile }: { compactOnMobile?: boolean }) {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const btnRef = useRef<HTMLButtonElement>(null);
  const location = useLocation();

  useEffect(() => setOpen(false), [location.pathname, location.search]);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false);
        btnRef.current?.focus();
      }
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  useEffect(() => {
    if (open) ref.current?.querySelector<HTMLElement>('.menu__item')?.focus();
  }, [open]);

  if (!user) return null;
  const staff = user.role === 'staff';
  return (
    <div className="menu-anchor" ref={ref}>
      <button
        ref={btnRef}
        type="button"
        className="avatar-btn"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Меню пользователя: ${user.display_name}`}
        onClick={() => setOpen((v) => !v)}
      >
        <Avatar initials={user.initials} staff={staff} />
        {!compactOnMobile && (
          <span className="avatar-btn__text">
            <span className="avatar-btn__name">{user.display_name}</span>
            <span className="avatar-btn__sub">{user.subtitle}</span>
          </span>
        )}
      </button>
      {open && (
        <div className="menu" role="menu" aria-label="Меню пользователя">
          <div className="menu__header">
            <div className="strong">{user.full_name}</div>
            <div className="xsmall muted">{user.subtitle}</div>
          </div>
          {!staff && (
            <>
              <Link className="menu__item" role="menuitem" to="/profile">
                <UserRound aria-hidden="true" />
                Профиль
              </Link>
              <Link className="menu__item" role="menuitem" to="/help">
                <CircleQuestionMark aria-hidden="true" />
                Помощь
              </Link>
            </>
          )}
          <button type="button" className="menu__item menu__item--danger" role="menuitem" onClick={() => void logout()}>
            <LogOut aria-hidden="true" />
            Выйти
          </button>
        </div>
      )}
    </div>
  );
}

function HelpButton() {
  return (
    <Link to="/help" className="icon-btn" aria-label="Помощь" title="Помощь">
      <CircleQuestionMark aria-hidden="true" />
    </Link>
  );
}

function Badge9({ n }: { n: number }) {
  if (n <= 0) return null;
  return (
    <span className="count-bubble" aria-hidden="true">
      {n > 9 ? '9+' : n}
    </span>
  );
}

function navAriaLabel(item: NavItem): string {
  if (!item.badge) return item.label;
  return `${item.label}, ${item.badge} ${plural(item.badge, ['непрочитанное', 'непрочитанных', 'непрочитанных'])}`;
}

export function AppShell({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const location = useLocation();
  const staff = user?.role === 'staff';
  const unread = useUnreadCount(!!user && !staff);

  const items: NavItem[] = staff
    ? [
        { to: '/staff', label: 'Заявки', icon: Inbox, match: ['/staff/applications'], end: false },
        { to: '/staff/grades', label: 'Баллы', icon: ChartColumn, match: ['/staff/grades'] },
        { to: '/staff/announcements', label: 'Объявления', icon: Megaphone, match: ['/staff/announcements'] },
      ]
    : [
        { to: '/', label: 'Главная', icon: House, match: [], end: true },
        { to: '/schedule', label: 'Расписание', icon: CalendarDays, match: ['/schedule'] },
        { to: '/study', label: 'Учёба', icon: GraduationCap, match: ['/study'] },
        { to: '/applications', label: 'Заявки', icon: FileText, match: ['/applications'] },
        { to: '/notifications', label: 'Уведомления', icon: Bell, match: ['/notifications'], badge: unread },
      ];

  const active = (item: NavItem) => {
    if (staff && item.to === '/staff') {
      return location.pathname === '/staff' || location.pathname.startsWith('/staff/applications');
    }
    return isActive(location.pathname, item);
  };

  const hideBottomNav = location.pathname === '/applications/new' && new URLSearchParams(location.search).has('type');
  const home = staff ? '/staff' : '/';

  // Позиции прокрутки по записям истории: при возврате «назад» пользователь оказывается там же, где был.
  const navType = useNavigationType();
  const positions = useRef(new Map<string, number>());
  const keyRef = useRef(location.key);
  keyRef.current = location.key;
  useEffect(() => {
    if ('scrollRestoration' in window.history) window.history.scrollRestoration = 'manual';
    let raf = 0;
    const onScroll = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => positions.current.set(keyRef.current, window.scrollY));
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      window.removeEventListener('scroll', onScroll);
      cancelAnimationFrame(raf);
    };
  }, []);

  // Фокус на заголовок при смене страницы — для экранного диктора и клавиатуры.
  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    const saved = navType === 'POP' ? positions.current.get(location.key) : undefined;
    if (saved != null && saved > 0) {
      // Данные страницы подгружаются асинхронно — ждём, пока высота позволит прокрутить (до 2 с).
      const started = performance.now();
      let raf = 0;
      const tryRestore = () => {
        if (document.documentElement.scrollHeight - window.innerHeight >= saved - 4) window.scrollTo(0, saved);
        else if (performance.now() - started < 2000) raf = requestAnimationFrame(tryRestore);
        else window.scrollTo(0, saved);
      };
      raf = requestAnimationFrame(tryRestore);
      return () => cancelAnimationFrame(raf);
    }
    window.scrollTo(0, 0);
    const t = window.setTimeout(() => {
      const h1 = document.getElementById('page-title');
      if (h1 && !document.activeElement?.closest('main')) h1.focus({ preventScroll: true });
    }, 60);
    return () => window.clearTimeout(t);
  }, [location.pathname]);

  return (
    <div className="app">
      <a href="#main" className="skip-link">
        Перейти к содержимому
      </a>
      <DisclaimerBar />
      <header className="app-header no-print">
        <Link to={home} className="logo" aria-label="На главную">
          <LogoMark className="logo__mark" />
        </Link>
        <span className="app-header__title">{sectionTitle(location.pathname)}</span>
        <div className="app-header__actions">
          {!staff && <HelpButton />}
          <UserMenu compactOnMobile />
        </div>
      </header>
      <div className="app-body">
        <aside className="sidebar no-print" aria-label="Основная навигация">
          <Logo to={home} tag={staff ? 'кабинет сотрудника' : 'концепт для конкурса'} />
          <nav className="sidebar__nav" aria-label="Разделы">
            {items.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className="sidebar__item"
                  aria-current={active(item) ? 'page' : undefined}
                  aria-label={navAriaLabel(item)}
                >
                  <Icon aria-hidden="true" />
                  <span>{item.label}</span>
                  {item.badge !== undefined && <Badge9 n={item.badge} />}
                </Link>
              );
            })}
          </nav>
          <div className="sidebar__foot">
            {!staff && (
              <Link to="/help" className="sidebar__item" aria-current={location.pathname === '/help' ? 'page' : undefined}>
                <CircleQuestionMark aria-hidden="true" />
                <span>Помощь</span>
              </Link>
            )}
            <p className="sidebar__note">Концепт для конкурса, не официальный сервис университета · Данные вымышлены</p>
          </div>
        </aside>
        <main id="main" className={`app-main ${hideBottomNav ? 'app-main--no-nav' : ''}`} tabIndex={-1}>
          <div className="desktop-topbar no-print">
            {!staff && <HelpButton />}
            <UserMenu />
          </div>
          <div className="app-content">{children}</div>
        </main>
      </div>
      {!hideBottomNav && (
        <nav className="bottom-nav no-print" aria-label="Разделы">
          {items.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.to}
                to={item.to}
                className="bottom-nav__item"
                aria-current={active(item) ? 'page' : undefined}
                aria-label={navAriaLabel(item)}
              >
                <span className="bottom-nav__icon">
                  <Icon aria-hidden="true" />
                  {item.badge !== undefined && item.badge > 0 && (
                    <span className="count-bubble bottom-nav__badge" aria-hidden="true">
                      {item.badge > 9 ? '9+' : item.badge}
                    </span>
                  )}
                </span>
                <span className="bottom-nav__label">{item.label}</span>
              </Link>
            );
          })}
        </nav>
      )}
    </div>
  );
}
