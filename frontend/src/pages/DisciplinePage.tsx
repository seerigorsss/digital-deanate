import { useMemo, useState, type FormEvent } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  BookOpen,
  CalendarClock,
  ChevronRight,
  FlaskConical,
  ListChecks,
  Mail,
  RotateCcw,
  Users,
} from 'lucide-react';
import { useDiscipline, useSimulate } from '../api/hooks';
import type { AnalyticsItem, DisciplineAnalytics, DisciplineDetail, Target } from '../api/types';
import { RiskBadge, TargetBadge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Callout } from '../components/ui/Callout';
import { Card, CardHeader } from '../components/ui/Card';
import { PageHeader } from '../components/ui/PageHeader';
import { ScoreBar } from '../components/domain/ScoreBar';
import { EmptyState, ErrorState, PageSkeleton } from '../components/ui/States';
import { ApiError } from '../api/client';
import { daysLeftLabel, fmtNum, formatDate, formatDay, weekdayShort } from '../lib/format';
import { MODULE_STATUS_LABEL, RISK_META } from '../lib/semantics';

const GRADE_TONE: Record<number, string> = { 85: 'grade--excellent', 71: 'grade--good', 60: 'grade--satisfactory' };

/** Итоговая оценка по сумме баллов (шкала ТЗ) — для блока «Что если». */
function gradeFor(a: DisciplineAnalytics, total: number, exam: number | null): { label: string; cls: string } {
  if (a.assessment_type === 'credit') return total >= a.passing_threshold ? { label: 'Зачёт', cls: 'grade--passed' } : { label: 'Незачёт', cls: 'grade--fail' };
  if (a.assessment_type === 'exam' && exam != null && exam < 18) return { label: 'Неудовлетворительно', cls: 'grade--fail' };
  if (total >= 85) return { label: 'Отлично', cls: 'grade--excellent' };
  if (total >= 71) return { label: 'Хорошо', cls: 'grade--good' };
  if (total >= 60) return { label: 'Удовлетворительно', cls: 'grade--satisfactory' };
  return { label: 'Неудовлетворительно', cls: 'grade--fail' };
}

function StatusBlock({ a }: { a: DisciplineAnalytics }) {
  const tone = RISK_META[a.risk.level]?.tone ?? 'nodata';
  return (
    <Card className="status-card" aria-labelledby="status-title">
      <div className="stack-sm">
        <h2 className="card-title" id="status-title">
          Текущая ситуация
        </h2>
        <span>
          <RiskBadge level={a.risk.level} label={a.risk.label} size="md" />
        </span>
      </div>
      <div className="stack-sm">
        <div className="big-points">
          <span className="big-points__value num">{fmtNum(a.current_semester_points + (a.exam?.result ?? 0))}</span>
          <span className="muted num">из 100</span>
        </div>
        <ScoreBar d={a} tone={tone} legend />
      </div>
    </Card>
  );
}

function targetLine(t: Target, a: DisciplineAnalytics): string {
  if (t.status === 'unreachable') return '';
  if (a.assessment_type === 'exam') {
    if (t.status === 'reached') return 'Получено';
    const sem = t.extra_semester_points_needed && t.extra_semester_points_needed > 0 ? `ещё ${fmtNum(t.extra_semester_points_needed)}` : 'достаточно';
    return `Семестр: ${sem} · Экзамен: от ${fmtNum(t.exam_points_needed ?? 18)}`;
  }
  if (t.status === 'reached') return 'Уже набрано';
  return `Ещё ${fmtNum(t.points_needed_semester ?? 0)} в семестре`;
}

function TargetsBlock({ a }: { a: DisciplineAnalytics }) {
  return (
    <Card aria-labelledby="targets-title">
      <CardHeader id="targets-title" title={a.assessment_type === 'credit' ? 'Получение зачёта' : 'Достижимость оценок'} level={2} />
      <ul className="record-list">
        {a.targets.map((t) => (
          <li key={t.threshold} className="target-row">
            <span className={`grade ${a.assessment_type === 'credit' ? 'grade--passed' : (GRADE_TONE[t.threshold] ?? '')}`}>
              {t.label} · {fmtNum(t.threshold)}
            </span>
            <TargetBadge status={t.status} />
            {targetLine(t, a) && <span className="target-row__line small">{targetLine(t, a)}</span>}
          </li>
        ))}
      </ul>
    </Card>
  );
}

function ItemRow({ it, today }: { it: AnalyticsItem; today: string }) {
  const overdue = it.state === 'pending' && it.due_date != null && it.due_date < today;
  return (
    <li className="item-row">
      <span className="item-row__body">
        <span className="item-row__title">{it.title}</span>
        <span className="item-row__meta xsmall muted">
          {it.due_date && (
            <>
              срок {formatDay(it.due_date)}
              {overdue && <span className="strong"> · срок прошёл, баллов пока нет</span>}
            </>
          )}
        </span>
      </span>
      <span className="item-row__points num">
        {it.state === 'graded' ? (
          <>
            <strong>{fmtNum(it.points)}</strong>
            <span className="muted"> / {fmtNum(it.max_points)}</span>
          </>
        ) : it.state === 'missing' ? (
          <span className="xsmall muted">нет данных · /{fmtNum(it.max_points)}</span>
        ) : (
          <span className="xsmall muted">ожидается · до {fmtNum(it.max_points)}</span>
        )}
      </span>
    </li>
  );
}

function ModulesBlock({ a }: { a: DisciplineAnalytics }) {
  return (
    <Card aria-labelledby="modules-title">
      <CardHeader id="modules-title" title="Модули и работы" icon={<ListChecks className="card-icon" aria-hidden="true" />} />
      <div>
        {a.modules.map((m) => (
          <details key={m.id} className="accordion" open={m.status !== 'completed' || m.missing > 0}>
            <summary>
              <span className="module-head">
                <span className="module-head__title">
                  Модуль {m.ordinal}. {m.title}
                </span>
                <span className="module-head__meta">
                  <span className={`badge badge--sm tone-${m.status === 'completed' ? 'nodata' : 'accent'}`}>
                    {MODULE_STATUS_LABEL[m.status]}
                  </span>
                  {m.ends_on && <span className="muted">до {formatDay(m.ends_on)}</span>}
                  {m.is_weak && <span className="badge badge--sm tone-medium">стоит повторить темы</span>}
                </span>
              </span>
              <span className="module-points num">
                <strong>{fmtNum(m.points)}</strong>
                <span className="muted">/{fmtNum(m.max_points)}</span>
              </span>
            </summary>
            <div className="accordion__body">
              <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
                {m.items.map((it) => (
                  <ItemRow key={it.id} it={it} today={a.as_of ?? ''} />
                ))}
              </ul>
            </div>
          </details>
        ))}
      </div>
    </Card>
  );
}

function WhatIf({ detail }: { detail: DisciplineDetail }) {
  const a = detail.analytics;
  const sim = useSimulate(detail.discipline.id);
  const pending = useMemo(() => a.modules.flatMap((m) => m.items.filter((i) => i.state === 'pending')), [a.modules]);
  const examAllowed = a.assessment_type === 'exam' && a.exam != null && a.exam.result == null;
  const [values, setValues] = useState<Record<number, string>>({});
  const [exam, setExam] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});

  if (pending.length === 0 && !examAllowed) return null;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const errs: Record<string, string> = {};
    const overrides: { item_id: number; points: number }[] = [];
    for (const it of pending) {
      const raw = (values[it.id] ?? '').trim().replace(',', '.');
      if (!raw) continue;
      const v = Number(raw);
      if (!Number.isFinite(v) || v < 0 || v > it.max_points) errs[String(it.id)] = `от 0 до ${fmtNum(it.max_points)}`;
      else overrides.push({ item_id: it.id, points: v });
    }
    let examPoints: number | null = null;
    if (examAllowed && exam.trim()) {
      const v = Number(exam.trim().replace(',', '.'));
      if (!Number.isFinite(v) || v < 0 || v > 30) errs.exam = 'от 0 до 30';
      else examPoints = v;
    }
    setErrors(errs);
    if (Object.keys(errs).length) return;
    sim.mutate({ overrides, exam_points: examPoints });
  };
  const reset = () => {
    setValues({});
    setExam('');
    setErrors({});
    sim.reset();
  };
  const fill = (share: number) => {
    // Округляем до 0,5 балла: так выглядят реальные оценки за работы.
    setValues(Object.fromEntries(pending.map((i) => [i.id, String(Math.round(i.max_points * share * 2) / 2)])));
    if (examAllowed) setExam(String(Math.round(30 * share * 2) / 2));
  };
  const r = sim.data?.analytics;
  const serverError = sim.error instanceof ApiError ? sim.error.message : sim.error ? 'Не удалось пересчитать. Попробуйте ещё раз.' : null;

  return (
    <Card className="whatif" aria-labelledby="whatif-title">
      <CardHeader id="whatif-title" title="Что если?" icon={<FlaskConical className="card-icon" aria-hidden="true" />} />
      <p className="small muted">Введите ожидаемые баллы — покажем итоговую оценку. Ничего не сохраняется.</p>
      <form onSubmit={submit} noValidate className="stack-sm">
        <div className="whatif__grid">
          {pending.map((it) => (
            <label key={it.id} className={`whatif-field ${errors[it.id] ? 'whatif-field--error' : ''}`}>
              <span className="whatif-field__label small">
                {it.title}
                {it.due_date && <span className="xsmall muted"> · {formatDay(it.due_date)}</span>}
              </span>
              <span className="whatif-field__input">
                <input
                  className="input"
                  inputMode="decimal"
                  value={values[it.id] ?? ''}
                  placeholder="—"
                  aria-invalid={!!errors[it.id]}
                  onChange={(e) => setValues((s) => ({ ...s, [it.id]: e.target.value }))}
                />
                <span className="whatif-field__suffix muted num">/ {fmtNum(it.max_points)}</span>
              </span>
              {errors[it.id] && <span className="field__error xsmall">Допустимо {errors[it.id]}</span>}
            </label>
          ))}
          {examAllowed && (
            <label className={`whatif-field ${errors.exam ? 'whatif-field--error' : ''}`}>
              <span className="whatif-field__label small strong">Экзамен</span>
              <span className="whatif-field__input">
                <input
                  className="input"
                  inputMode="decimal"
                  value={exam}
                  placeholder="—"
                  aria-invalid={!!errors.exam}
                  onChange={(e) => setExam(e.target.value)}
                />
                <span className="whatif-field__suffix muted num">/ 30</span>
              </span>
              {errors.exam && <span className="field__error xsmall">Допустимо {errors.exam}</span>}
            </label>
          )}
        </div>
        <div className="row-wrap">
          <Button type="submit" variant="primary" loading={sim.isPending}>
            Пересчитать
          </Button>
          {(pending.length > 0 || examAllowed) && (
            <>
              <Button type="button" variant="ghost" onClick={() => fill(0.6)}>
                Заполнить минимумом
              </Button>
              <Button type="button" variant="ghost" onClick={() => fill(1)}>
                Заполнить максимумом
              </Button>
            </>
          )}
          <Button type="button" variant="ghost" icon={<RotateCcw size={16} />} onClick={reset} disabled={!r && !Object.keys(values).length && !exam}>
            Сбросить
          </Button>
        </div>
        {serverError && (
          <Callout tone="critical" role="alert">
            {serverError}
          </Callout>
        )}
      </form>
      {r && (
        <div className="whatif-result" aria-live="polite">
          {(() => {
            const examPts = r.exam?.result ?? null;
            const needExam = a.assessment_type === 'exam' && examPts == null;
            const total = r.current_semester_points + (examPts ?? 0);
            if (needExam)
              return (
                <p className="small">
                  Семестр: <strong className="num">{fmtNum(r.current_semester_points)}</strong> из {fmtNum(r.semester_points_max)}. Укажите баллы за
                  экзамен, чтобы увидеть итоговую оценку.
                </p>
              );
            const g = gradeFor(a, total, examPts);
            return (
              <div className="row-wrap">
                <span className="small muted">Итог:</span>
                <span className={`grade ${g.cls}`}>{g.label}</span>
                <span className="small muted num">{fmtNum(total)} из 100</span>
              </div>
            );
          })()}
        </div>
      )}
    </Card>
  );
}

function TopicsBlock({ detail }: { detail: DisciplineDetail }) {
  const topics = detail.topics;
  return (
    <Card aria-labelledby="topics-title">
      <CardHeader id="topics-title" title="Темы и материалы" icon={<BookOpen className="card-icon" aria-hidden="true" />} />
      {topics.length === 0 ? (
        <EmptyState compact title="Темы дисциплины не указаны" />
      ) : (
        <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
          {topics.map((t) => (
            <li key={t.id}>
              <Link to={`/study/${detail.discipline.id}/topics/${t.id}`} className="topic-row">
                <span className="topic-row__body">
                  <span className="topic-row__title">{t.title}</span>
                  <span className="xsmall muted">
                    {t.module_ordinal ? `Модуль ${t.module_ordinal}` : ''}
                    {t.resources_count > 0 ? ` · материалов: ${t.resources_count}` : ' · материалы пока не подобраны'}
                  </span>
                </span>
                {t.is_weak && <span className="badge badge--sm tone-medium">стоит повторить</span>}
                <ChevronRight size={18} aria-hidden="true" />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function SideInfo({ detail }: { detail: DisciplineDetail }) {
  const a = detail.analytics;
  const d = detail.discipline;
  return (
    <>
      {a.next_actions.length > 0 && (
        <Card aria-labelledby="next-title">
          <CardHeader id="next-title" title="Ближайшие работы" icon={<CalendarClock className="card-icon" aria-hidden="true" />} />
          <ul className="stack-sm" style={{ listStyle: 'none', margin: 0, padding: 0 }}>
            {a.next_actions.map((n) => (
              <li key={n.item_id} className="row-wrap" style={{ justifyContent: 'space-between' }}>
                <span>
                  <span className="strong">{n.title}</span>
                  <span className="xsmall muted"> · до {fmtNum(n.max_points)} баллов</span>
                </span>
                {n.due_date && (
                  <span className={`xsmall num ${n.overdue ? 'strong' : 'muted'}`}>
                    {weekdayShort(n.due_date)}, {formatDay(n.due_date)}
                    {n.days_left != null && ` · ${n.overdue ? 'срок прошёл' : daysLeftLabel(n.days_left)}`}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </Card>
      )}
      <Card aria-labelledby="teachers-title">
        <CardHeader id="teachers-title" title="Преподаватели" icon={<Users className="card-icon" aria-hidden="true" />} />
        <ul className="stack-sm" style={{ listStyle: 'none', margin: 0, padding: 0 }}>
          {(detail.teachers.length ? detail.teachers : d.lecturer ? [{ ...d.lecturer, roles: ['лекции'] }] : []).map((t) => (
            <li key={t.id} className="stack-xs">
              <span className="strong">{t.full_name}</span>
              <span className="xsmall muted">
                {[t.position, t.roles.join(', ')].filter(Boolean).join(' · ')}
              </span>
              {t.email && (
                <a className="xsmall" href={`mailto:${t.email}`}>
                  <Mail size={12} aria-hidden="true" /> {t.email}
                </a>
              )}
            </li>
          ))}
        </ul>
        {d.exam_date && (
          <p className="small" style={{ marginTop: 12 }}>
            Экзамен: <strong>{formatDate(d.exam_date)}</strong>
            {d.exam_room ? `, ${d.exam_room}` : ''}
          </p>
        )}
      </Card>
    </>
  );
}

export default function DisciplinePage() {
  const { disciplineId } = useParams();
  const id = Number(disciplineId);
  const q = useDiscipline(id);

  if (!Number.isFinite(id)) return <EmptyState title="Дисциплина не найдена" />;
  if (q.isPending) return <PageSkeleton cards={4} />;
  if (q.isError)
    return (
      <div className="stack">
        <PageHeader title="Дисциплина" back={{ to: '/study', label: 'Учёба' }} />
        <Card>
          <ErrorState error={q.error} onRetry={() => void q.refetch()} retrying={q.isFetching} />
        </Card>
      </div>
    );
  const detail = q.data;
  const d = detail.discipline;
  const a = detail.analytics;
  return (
    <div className="stack">
      <PageHeader
        title={d.title}
        back={{ to: '/study', label: 'Учёба' }}
        subtitle={[a.assessment_type_label, d.credits ? `${d.credits} ЗЕ` : null, d.department].filter(Boolean).join(' · ')}
      />
      <StatusBlock a={a} />
      <div className="grid-2">
        <div className="col stack">
          <TargetsBlock a={a} />
          <ModulesBlock a={a} />
          <WhatIf detail={detail} />
        </div>
        <div className="col stack">
          <TopicsBlock detail={detail} />
          <SideInfo detail={detail} />
        </div>
      </div>
    </div>
  );
}
