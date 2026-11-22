import { Link } from 'react-router-dom';
import { ArrowRightLeft, CalendarPlus, CalendarX, MapPin, UserRound } from 'lucide-react';
import type { Lesson } from '../../api/types';
import { formatDay, weekdayShort } from '../../lib/format';
import { Badge } from '../ui/Badge';

/** Сокращение ФИО: «Белов Андрей Викторович» → «Белов А. В.» */
export function shortName(full: string | null | undefined): string {
  if (!full) return '';
  const [last, ...rest] = full.split(/\s+/);
  return [last, ...rest.map((p) => `${p[0]}.`)].join(' ');
}

function changeBadge(lesson: Lesson) {
  const c = lesson.change;
  switch (lesson.status) {
    case 'cancelled':
      return { icon: CalendarX, label: 'Отменено' };
    case 'moved_out':
    case 'moved_in':
      return { icon: ArrowRightLeft, label: lesson.status === 'moved_in' ? 'Перенесено сюда' : 'Перенесено' };
    case 'added':
      return { icon: CalendarPlus, label: 'Дополнительное занятие' };
    case 'changed':
      if (c?.type === 'teacher') return { icon: UserRound, label: 'Замена преподавателя' };
      return { icon: MapPin, label: 'Аудитория изменена' };
    default:
      return null;
  }
}

function when(date: string | null | undefined, time: string | null | undefined): string {
  if (!date) return time ?? '';
  return `${weekdayShort(date)}, ${formatDay(date)}${time ? `, ${time}` : ''}`;
}

interface LessonCardProps {
  lesson: Lesson;
  compact?: boolean;
  next?: boolean;
}

/**
 * Карточка занятия. Изменения показаны цветом (фиолетовая полоса — не цвет риска), меткой с иконкой
 * и текстом «было → стало»; у зачёркнутого текста есть словесная альтернатива для экранного диктора.
 */
export function LessonCard({ lesson, compact, next }: LessonCardProps) {
  const badge = changeBadge(lesson);
  const c = lesson.change;
  const cancelled = lesson.status === 'cancelled' || lesson.status === 'moved_out';
  const changed = lesson.status !== 'normal';
  const classes = ['lesson', changed ? 'lesson--changed' : '', cancelled ? 'lesson--cancelled' : '', compact ? 'lesson--compact' : '']
    .filter(Boolean)
    .join(' ');

  let detail: { aria: string; node: JSX.Element } | null = null;
  if (lesson.status === 'changed' && c?.type === 'room' && c.old_room) {
    detail = {
      aria: `Аудитория изменена: была ${c.old_room}, теперь ${lesson.room}`,
      node: (
        <>
          <s>{c.old_room}</s> → <strong>{lesson.room}</strong>
        </>
      ),
    };
  } else if (lesson.status === 'changed' && c?.type === 'teacher' && c.old_teacher) {
    detail = {
      aria: `Замена преподавателя: был ${c.old_teacher.full_name}, теперь ${lesson.teacher?.full_name ?? ''}`,
      node: (
        <>
          <s>{shortName(c.old_teacher.full_name)}</s> → <strong>{shortName(lesson.teacher?.full_name)}</strong>
        </>
      ),
    };
  } else if (lesson.status === 'moved_out' && c) {
    const target = when(c.new_date, c.new_start_time);
    detail = { aria: `Перенесено на ${target}`, node: <>Перенесено на {target}</> };
  } else if (lesson.status === 'moved_in' && c) {
    const from = when(c.original_date, c.original_start_time);
    detail = { aria: `Перенесено с ${from}`, node: <>Перенесено с {from}</> };
  } else if (lesson.status === 'cancelled') {
    detail = { aria: 'Занятие отменено', node: <>Занятие отменено</> };
  } else if (lesson.status === 'added') {
    detail = { aria: 'Добавлено деканатом', node: <>Добавлено деканатом</> };
  }

  const title = lesson.discipline_id ? (
    <Link to={`/study/${lesson.discipline_id}`} className="lesson__title-link">
      {lesson.discipline_title}
    </Link>
  ) : (
    lesson.discipline_title
  );

  return (
    <article className={classes}>
      <div className="lesson__time num">
        <span className="lesson__start">{lesson.start_time}</span>
        <span className="lesson__end">{lesson.end_time}</span>
      </div>
      <div className="lesson__body">
        {(badge || next) && (
          <div className="row-wrap lesson__badges">
            {next && !cancelled && <Badge tone="accent">Далее</Badge>}
            {badge && (
              <Badge tone="change" icon={<badge.icon aria-hidden="true" />}>
                {badge.label}
              </Badge>
            )}
          </div>
        )}
        <h3 className="lesson__title">{title}</h3>
        <div className="lesson__meta">
          <span className="badge badge--plain">{lesson.lesson_type_label}</span>
          {lesson.room && (
            <span className="lesson__meta-item">
              <MapPin aria-hidden="true" />
              {lesson.room}
            </span>
          )}
          {lesson.teacher && !compact && (
            <span className="lesson__meta-item">
              <UserRound aria-hidden="true" />
              <span>
                {lesson.teacher.full_name}
                {lesson.teacher.position && <span className="muted">, {lesson.teacher.position}</span>}
              </span>
            </span>
          )}
          {lesson.teacher && compact && (
            <span className="lesson__meta-item">
              <UserRound aria-hidden="true" />
              {shortName(lesson.teacher.full_name)}
            </span>
          )}
        </div>
        {detail && (
          <p className="lesson__change">
            <span className="sr-only">{detail.aria}</span>
            <span aria-hidden="true">{detail.node}</span>
          </p>
        )}
        {c?.reason && !compact && <p className="lesson__reason">Причина: {c.reason}</p>}
      </div>
    </article>
  );
}
