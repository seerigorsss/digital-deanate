import { useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { CalendarDays, ChevronLeft, ChevronRight, Sparkles } from 'lucide-react';
import { useMeta, useSchedule } from '../api/hooks';
import type { ScheduleDay } from '../api/types';
import { LessonCard } from '../components/domain/LessonCard';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { PageHeader } from '../components/ui/PageHeader';
import { Segmented } from '../components/ui/Segmented';
import { EmptyState, ErrorState, PageSkeleton, Skeleton } from '../components/ui/States';
import {
  addDays,
  dayOfMonth,
  formatDay,
  formatRange,
  isValidISODate,
  mondayOf,
  plural,
  weekdayName,
  weekdayShort,
} from '../lib/format';

type View = 'day' | 'week';

function countChanges(days: ScheduleDay[]): number {
  const seen = new Set<string>();
  let n = 0;
  for (const d of days) {
    for (const l of d.lessons) {
      if (l.status === 'normal') continue;
      // Перенос — одно изменение, даже если на неделе видны обе его стороны.
      const key = l.status === 'moved_in' || l.status === 'moved_out' ? `move:${l.change?.text ?? l.key}` : l.key;
      if (seen.has(key)) continue;
      seen.add(key);
      n += 1;
    }
  }
  return n;
}

function DayStrip({ days, selected, today, onSelect }: { days: ScheduleDay[]; selected: string; today: string; onSelect: (d: string) => void }) {
  return (
    <div className="day-strip" role="group" aria-label="Выбор дня недели">
      {days.map((d) => {
        const isSel = d.date === selected;
        const changes = d.lessons.some((l) => l.status !== 'normal');
        return (
          <button
            key={d.date}
            type="button"
            className={`day-strip__item ${d.date === today ? 'day-strip__item--today' : ''}`}
            aria-pressed={isSel}
            aria-label={`${weekdayName(d.date)}, ${formatDay(d.date)}${d.date === today ? ', сегодня' : ''}, ${d.lessons.length} ${plural(d.lessons.length, ['занятие', 'занятия', 'занятий'])}${changes ? ', есть изменения' : ''}`}
            onClick={() => onSelect(d.date)}
          >
            <span className="day-strip__wd">{weekdayShort(d.date)}</span>
            <span className="day-strip__num num">{dayOfMonth(d.date)}</span>
            <span className={`day-strip__dot ${changes ? 'day-strip__dot--on' : ''}`} aria-hidden="true" />
          </button>
        );
      })}
    </div>
  );
}

function DayList({ day, today, compact }: { day: ScheduleDay; today: string; compact?: boolean }) {
  if (day.lessons.length === 0) {
    return (
      <EmptyState
        compact
        icon={<CalendarDays />}
        title={day.date === today ? 'Сегодня занятий нет' : 'В этот день занятий нет'}
        text={compact ? undefined : 'Можно посмотреть другие дни недели.'}
      />
    );
  }
  return (
    <div className="lesson-list">
      {day.lessons.map((l) => (
        <LessonCard key={l.key} lesson={l} compact={compact} />
      ))}
    </div>
  );
}

export default function SchedulePage() {
  const meta = useMeta();
  const [params, setParams] = useSearchParams();
  const today = meta.data?.today;
  const rawDate = params.get('date');
  const date = isValidISODate(rawDate) ? rawDate : today ?? '';
  const view: View = params.get('view') === 'week' ? 'week' : 'day';
  const monday = date ? mondayOf(date) : '';
  const sunday = monday ? addDays(monday, 6) : '';
  const q = useSchedule(monday, sunday, !!monday);

  const go = (next: { date?: string; view?: View }) => {
    const p = new URLSearchParams(params);
    if (next.date) p.set('date', next.date);
    if (next.view) {
      if (next.view === 'week') p.set('view', 'week');
      else p.delete('view');
    }
    setParams(p);
  };

  const visibleDays = useMemo(() => {
    const days = q.data?.days ?? [];
    return days.filter((d) => d.weekday < 6 || d.lessons.length > 0);
  }, [q.data]);

  if (meta.isPending) return <PageSkeleton />;
  if (meta.isError)
    return (
      <Card>
        <ErrorState
          error={meta.error}
          onRetry={() => {
            void meta.refetch();
            void q.refetch();
          }}
        />
      </Card>
    );

  const data = q.data && q.data.date_from === monday ? q.data : undefined;
  const period = q.data?.period;
  const canPrev = !period || addDays(monday, -1) >= period.starts_on;
  const canNext = !period || addDays(monday, 7) <= period.ends_on;
  const first = data?.days[0];
  const isCurrentWeek = today ? mondayOf(today) === monday : false;
  const changes = data ? countChanges(data.days) : 0;
  const selectedDay = data?.days.find((d) => d.date === date);

  return (
    <div className="stack">
      <PageHeader
        title="Расписание"
        subtitle={q.data ? `Группа ${q.data.group} · ${q.data.period.title}` : undefined}
        actions={
          <Segmented
            label="Режим просмотра"
            value={view}
            onChange={(v) => go({ view: v })}
            options={[
              { value: 'day', label: 'День' },
              { value: 'week', label: 'Неделя' },
            ]}
          />
        }
      />

      <div className="week-nav">
        <Button
          variant="default"
          className="week-nav__arrow"
          aria-label="Предыдущая неделя"
          title="Предыдущая неделя"
          disabled={!canPrev}
          onClick={() => go({ date: addDays(monday, -7) })}
          icon={<ChevronLeft aria-hidden="true" />}
        />
        <div className="week-nav__label" aria-live="polite">
          <span className="strong num">{formatRange(monday, addDays(monday, 6))}</span>
          {first && (
            <span className="small text-2 num">
              {first.week_number}-я неделя · {first.week_parity_label.toLowerCase()}
            </span>
          )}
        </div>
        <Button
          variant="default"
          className="week-nav__arrow"
          aria-label="Следующая неделя"
          title="Следующая неделя"
          disabled={!canNext}
          onClick={() => go({ date: addDays(monday, 7) })}
          icon={<ChevronRight aria-hidden="true" />}
        />
        {today && (!isCurrentWeek || date !== today) && (
          <Button variant="secondary" size="sm" className="week-nav__today" onClick={() => go({ date: today })}>
            Сегодня
          </Button>
        )}
      </div>
      {(!canPrev || !canNext) && <p className="xsmall muted">Расписание доступно только на текущий семестр.</p>}

      {q.isError && !data ? (
        <Card>
          <ErrorState
            error={q.error}
            onRetry={() => {
              void meta.refetch();
              void q.refetch();
            }}
            retrying={q.isFetching}
            title="Не удалось загрузить расписание"
          />
        </Card>
      ) : !data ? (
        <div className="stack" aria-busy="true">
          <span className="sr-only" role="status">
            Загрузка расписания…
          </span>
          <Skeleton height={64} radius={14} />
          <Skeleton height={110} radius={16} />
          <Skeleton height={110} radius={16} />
        </div>
      ) : (
        <>
          <div className={`changes-summary ${changes ? 'tone-change' : 'tone-neutral'}`} role="status">
            <Sparkles aria-hidden="true" />
            {changes
              ? `На этой неделе ${changes} ${plural(changes, ['изменение', 'изменения', 'изменений'])} в расписании — они выделены`
              : 'Изменений на этой неделе нет'}
          </div>

          {view === 'day' ? (
            <>
              <DayStrip days={visibleDays} selected={date} today={today ?? ''} onSelect={(d) => go({ date: d })} />
              <section aria-labelledby="day-title" className="stack-sm">
                <h2 className="day-title" id="day-title">
                  {weekdayName(date)}, {formatDay(date)}
                  {date === today && <Badge tone="accent">Сегодня</Badge>}
                </h2>
                {selectedDay ? <DayList day={selectedDay} today={today ?? ''} /> : null}
              </section>
            </>
          ) : (
            <div className="week-grid">
              {visibleDays.map((d) => (
                <section key={d.date} className={`week-day ${d.date === today ? 'week-day--today' : ''}`} aria-labelledby={`wd-${d.date}`}>
                  <header className="week-day__head">
                    <h2 id={`wd-${d.date}`} className="week-day__title">
                      <Link to={`/schedule?date=${d.date}`}>
                        {weekdayName(d.date)}, {formatDay(d.date)}
                      </Link>
                    </h2>
                    {d.date === today && <Badge tone="accent">Сегодня</Badge>}
                    {d.changes_count > 0 && (
                      <Badge tone="change">
                        {d.changes_count} {plural(d.changes_count, ['изменение', 'изменения', 'изменений'])}
                      </Badge>
                    )}
                  </header>
                  <DayList day={d} today={today ?? ''} compact />
                </section>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
