import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlarmClock,
  Bell,
  CalendarDays,
  CalendarRange,
  ChevronRight,
  FileCheck,
  FileText,
  GraduationCap,
  MessageCircleQuestion,
  MessagesSquare,
  Sunrise,
} from 'lucide-react';
import { useDashboard, useMarkRead } from '../api/hooks';
import type { Dashboard, NotificationItem } from '../api/types';
import { ApplicationRow } from '../components/domain/ApplicationRow';
import { LessonCard } from '../components/domain/LessonCard';
import { NotificationRow } from '../components/domain/NotificationRow';
import { NotificationDetail } from '../components/domain/NotificationDetail';
import { ZoneChips } from '../components/domain/ZoneChips';
import { RiskBadge, ZoneBadge } from '../components/ui/Badge';
import { Button, ButtonLink } from '../components/ui/Button';
import { Card, CardHeader } from '../components/ui/Card';
import { IndexScale } from '../components/ui/Gauge';
import { useDocumentTitle } from '../components/ui/PageHeader';
import { EmptyState, ErrorState, Skeleton, SkeletonCard } from '../components/ui/States';
import { daysLeftLabel, formatDay, fmtNum, greeting, weekdayName, weekdayShort } from '../lib/format';
import { useAuth } from '../auth/AuthContext';

function TodayBlock({ d }: { d: Dashboard }) {
  const next = d.next_lesson;
  const lessons = d.today_lessons;
  return (
    <Card aria-labelledby="today-title">
      <CardHeader
        id="today-title"
        title="Сегодня"
        icon={<Sunrise className="card-icon" aria-hidden="true" />}
        link={{ to: `/schedule?date=${d.today}`, label: 'Всё расписание' }}
      />
      {lessons.length > 0 ? (
        <div className="lesson-list">
          {lessons.map((l) => (
            <LessonCard key={l.key} lesson={l} compact next={!!next && next.date === d.today && next.lesson.key === l.key} />
          ))}
        </div>
      ) : (
        <EmptyState
          compact
          icon={<CalendarDays />}
          title="Сегодня занятий нет"
          text={
            next ? (
              <>
                Следующее занятие: {weekdayShort(next.date)}, {formatDay(next.date)}, {next.lesson.start_time} —{' '}
                {next.lesson.discipline_title}, {next.lesson.lesson_type_label.toLowerCase()}
                {next.lesson.room ? `, ${next.lesson.room}` : ''}
              </>
            ) : (
              'Ближайших занятий в расписании нет.'
            )
          }
          actions={
            next && (
              <ButtonLink to={`/schedule?date=${next.date}`} variant="ghost" size="sm">
                Показать {weekdayName(next.date).toLowerCase()}
              </ButtonLink>
            )
          }
        />
      )}
    </Card>
  );
}

function IndexBlock({ d }: { d: Dashboard }) {
  const { index, zone_counts, priorities } = d.analytics;
  return (
    <Card aria-labelledby="index-title">
      <CardHeader
        id="index-title"
        title="Успеваемость"
        icon={<GraduationCap className="card-icon" aria-hidden="true" />}
        link={{ to: '/study', label: 'Радар' }}
      />
      {index.value === null ? (
        <p className="text-2">Показатель появится, когда преподаватели внесут первые баллы.</p>
      ) : (
        <div className="stack-sm">
          <div className="row-wrap" style={{ gap: 12 }}>
            <span className="index-number num">{index.value}</span>
            <span className="muted">из {index.max}</span>
            <ZoneBadge zone={index.zone} label={index.label} size="md" />
          </div>
          <IndexScale value={index.value} zone={index.zone} label={index.label} />
        </div>
      )}
      <div style={{ marginTop: 16 }}>
        <ZoneChips counts={zone_counts} />
      </div>
      <div className="card__footer">
        {priorities.length > 0 ? (
          <div className="stack-xs">
            <span className="xsmall muted strong">Стоит подтянуть</span>
            <ul className="list" style={{ margin: 0 }}>
              {priorities.map((p) => (
                <li key={p.discipline_id}>
                  <Link to={`/study/${p.discipline_id}`} className="list-row">
                    <span className="list-row__body">
                      <span className="list-row__title">{p.title}</span>
                    </span>
                    <RiskBadge level={p.risk_level} label={p.risk_label ?? undefined} />
                    <ChevronRight className="list-row__chevron" aria-hidden="true" />
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <p className="small text-2">Сейчас ничего не требует срочного внимания.</p>
        )}
      </div>
    </Card>
  );
}

function QuickActions() {
  const actions = [
    { to: '/applications/new?type=study_certificate', label: 'Заказать справку', icon: FileCheck },
    { to: '/applications/new?type=dean_question', label: 'Написать в деканат', icon: MessagesSquare },
    { to: '/study', label: 'Успеваемость', icon: GraduationCap },
    { to: '/schedule?view=week', label: 'Расписание на неделю', icon: CalendarRange },
  ];
  return (
    <section aria-labelledby="qa-title">
      <h2 className="sr-only" id="qa-title">
        Быстрые действия
      </h2>
      <ul className="quick-actions">
        {actions.map((a) => (
          <li key={a.to}>
            <Link to={a.to} className="quick-action">
              <span className="quick-action__icon" aria-hidden="true">
                <a.icon />
              </span>
              <span>{a.label}</span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

function DeadlinesBlock({ d }: { d: Dashboard }) {
  const [all, setAll] = useState(false);
  const items = all ? d.deadlines : d.deadlines.slice(0, 4);
  return (
    <Card aria-labelledby="dl-title">
      <CardHeader id="dl-title" title="Ближайшие сроки" icon={<AlarmClock className="card-icon" aria-hidden="true" />} />
      {d.deadlines.length === 0 ? (
        <EmptyState compact icon={<AlarmClock />} title="Ближайших сроков нет" text="В ближайшие три недели нет работ без оценки." />
      ) : (
        <>
          <ul className="list">
            {items.map((x) => (
              <li key={x.item_id}>
                <Link to={`/study/${x.discipline_id}`} className="list-row">
                  <span className={`deadline-date ${x.days_left <= 3 ? 'deadline-date--soon' : ''}`} aria-hidden="true">
                    <span className="deadline-date__day num">{new Date(`${x.due_date}T12:00:00Z`).getUTCDate()}</span>
                    <span className="deadline-date__wd">{weekdayShort(x.due_date)}</span>
                  </span>
                  <span className="list-row__body">
                    <span className="list-row__title">
                      {x.title} · {x.discipline_short || x.discipline_title}
                    </span>
                    <span className="list-row__meta num">
                      {weekdayShort(x.due_date)}, {formatDay(x.due_date)} · {daysLeftLabel(x.days_left)} · до {fmtNum(x.max_points)}{' '}
                      баллов
                    </span>
                  </span>
                  <ChevronRight className="list-row__chevron" aria-hidden="true" />
                </Link>
              </li>
            ))}
          </ul>
          {d.deadlines.length > 4 && (
            <Button variant="ghost" size="sm" onClick={() => setAll((v) => !v)} aria-expanded={all}>
              {all ? 'Свернуть' : `Показать ещё ${d.deadlines.length - 4}`}
            </Button>
          )}
        </>
      )}
    </Card>
  );
}

function ApplicationsBlock({ d }: { d: Dashboard }) {
  return (
    <Card aria-labelledby="apps-title">
      <CardHeader
        id="apps-title"
        title="Мои заявки"
        icon={<FileText className="card-icon" aria-hidden="true" />}
        link={{ to: '/applications', label: 'Все заявки' }}
      />
      {d.applications.length === 0 ? (
        <EmptyState
          compact
          icon={<FileText />}
          title="Активных заявок нет"
          actions={
            <ButtonLink to="/applications/new?type=study_certificate" variant="secondary" size="sm">
              Заказать справку
            </ButtonLink>
          }
        />
      ) : (
        <ul className="list">
          {d.applications.map((a) => (
            <li key={a.id}>
              <ApplicationRow app={a} today={d.today} />
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function NotificationsBlock({ d }: { d: Dashboard }) {
  const markRead = useMarkRead();
  const [selected, setSelected] = useState<NotificationItem | null>(null);
  const open = (n: NotificationItem) => {
    if (!n.is_read) markRead.mutate(n.id);
    setSelected(n);
  };
  const unread = d.notifications.unread_count;
  return (
    <Card aria-labelledby="notif-title">
      <CardHeader
        id="notif-title"
        title="Уведомления"
        icon={<Bell className="card-icon" aria-hidden="true" />}
        link={{ to: '/notifications', label: unread > 0 ? `Все · ${unread} новых` : 'Все' }}
      />
      {d.notifications.latest.length === 0 ? (
        <EmptyState compact icon={<Bell />} title="Новых уведомлений нет" />
      ) : (
        <div className="notif-list notif-list--plain">
          {d.notifications.latest.map((n) => (
            <NotificationRow key={n.id} n={n} onOpen={open} clamp />
          ))}
        </div>
      )}
      <NotificationDetail n={selected} onClose={() => setSelected(null)} />
    </Card>
  );
}

function NeedsReplyBanner({ d }: { d: Dashboard }) {
  const waiting = d.applications.filter((a) => a.status === 'needs_info').slice(0, 2);
  if (waiting.length === 0) return null;
  return (
    <div className="stack-sm">
      {waiting.map((a) => (
        <div key={a.id} className="callout tone-attention reply-banner" role="status">
          <MessageCircleQuestion aria-hidden="true" />
          <div className="callout__body">
            <div className="callout__title">Деканат ждёт вашего ответа</div>
            <div>по заявке «{a.title}», № {a.number}</div>
          </div>
          <ButtonLink to={`/applications/${a.id}#reply`} variant="primary" size="sm">
            Ответить
          </ButtonLink>
        </div>
      ))}
    </div>
  );
}

function HomeSkeleton() {
  return (
    <div className="stack" aria-busy="true">
      <span className="sr-only" role="status">
        Загрузка главной…
      </span>
      <Skeleton width="60%" height={30} radius={10} />
      <Skeleton width="45%" height={16} />
      <div className="grid-2">
        <div className="col">
          <SkeletonCard lines={4} />
          <SkeletonCard height={90} />
        </div>
        <div className="col">
          <SkeletonCard height={120} />
          <SkeletonCard lines={3} />
        </div>
      </div>
    </div>
  );
}

export function HomePage() {
  useDocumentTitle('Главная');
  const { user } = useAuth();
  const q = useDashboard();

  if (q.isPending) return <HomeSkeleton />;
  if (q.isError)
    return (
      <Card>
        <ErrorState error={q.error} onRetry={() => void q.refetch()} retrying={q.isFetching} />
      </Card>
    );
  const d = q.data;
  const p = d.period;
  return (
    <div className="stack">
      <header className="home-hello">
        <h1 className="page-title" id="page-title" tabIndex={-1}>
          {greeting()}, {d.first_name || user?.display_name}
        </h1>
        <p className="page-subtitle num">
          {weekdayName(d.today)}, {formatDay(d.today)} · {p.week_number}-я неделя, {p.week_parity_label.toLowerCase()}
        </p>
        <div className="semester-progress">
          <div className="progress" aria-hidden="true">
            <div className="progress__bar" style={{ width: `${Math.round(p.semester_progress * 100)}%` }} />
          </div>
          <span className="xsmall muted num">
            Семестр пройден на {Math.round(p.semester_progress * 100)}% · сессия с {formatDay(p.session_starts_on)}
          </span>
        </div>
      </header>

      <NeedsReplyBanner d={d} />

      <div className="grid-2 home-grid">
        <div className="col">
          <div className="home-o1">
            <TodayBlock d={d} />
          </div>
          <div className="home-o2">
            <IndexBlock d={d} />
          </div>
          <div className="home-o4">
            <DeadlinesBlock d={d} />
          </div>
        </div>
        <div className="col">
          <div className="home-o3">
            <QuickActions />
          </div>
          <div className="home-o5">
            <ApplicationsBlock d={d} />
          </div>
          <div className="home-o6">
            <NotificationsBlock d={d} />
          </div>
        </div>
      </div>
    </div>
  );
}
