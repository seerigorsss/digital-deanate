import { useMemo, useState, type FormEvent } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  AlertTriangle,
  BookOpen,
  CalendarClock,
  ChevronRight,
  FlaskConical,
  GraduationCap,
  Lightbulb,
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
import { PointsBar, type BarMark } from '../components/ui/PointsBar';
import { EmptyState, ErrorState, PageSkeleton } from '../components/ui/States';
import { ApiError } from '../api/client';
import { daysLeftLabel, fmtNum, fmtPercent, formatDate, formatDay, itemKindLabel, weekdayShort } from '../lib/format';
import { MODULE_STATUS_LABEL, RISK_META } from '../lib/semantics';

function marksFor(a: DisciplineAnalytics): BarMark[] {
  if (a.assessment_type === 'exam') {
    return [
      { value: 30, label: '30' },
      { value: a.semester_target, label: `${fmtNum(a.semester_target)}` },
    ];
  }
  const ts = a.targets.map((t) => t.threshold).filter((v) => v <= a.semester_points_max);
  return ts.map((v) => ({ value: v, label: fmtNum(v) }));
}

function targetNeed(t: Target, a: DisciplineAnalytics): string | null {
  if (a.assessment_type === 'exam') {
    if (t.status === 'unreachable') return null;
    if (t.reachable_with_current_points && t.exam_points_needed != null)
      return `Семестровых баллов достаточно — на экзамене нужно ${fmtNum(t.exam_points_needed)} из 30`;
    if (t.extra_semester_points_needed && t.extra_semester_points_needed > 0)
      return `Добрать ${fmtNum(t.extra_semester_points_needed)} в семестре и сдать экзамен на ${fmtNum(t.exam_points_needed ?? 30)}`;
    if (t.exam_points_needed != null) return `На экзамене — от ${fmtNum(t.exam_points_needed)} баллов`;
    return null;
  }
  if (t.status === 'reached' || t.status === 'unreachable') return null;
  if (t.points_needed_semester != null && t.points_needed_semester > 0)
    return `Нужно ещё ${fmtNum(t.points_needed_semester)}${
      t.required_share_of_remaining != null ? ` — ${fmtPercent(t.required_share_of_remaining)} оставшихся баллов` : ''
    }`;
  return null;
}

/** Пояснение без предложений, которые уже показаны в списке причин. */
function explanationRest(a: DisciplineAnalytics): string {
  const norm = (x: string) => x.replace(/[.\s]+$/, '').trim().toLowerCase();
  const reasons = a.risk.reasons.map(norm);
  const sentences = a.explanation.split(/(?<=[.!?])\s+/).filter((x) => x.trim());
  return sentences.filter((s) => !reasons.some((r) => r.includes(norm(s)) || norm(s).includes(r))).join(' ');
}

function StatusBlock({ a }: { a: DisciplineAnalytics }) {
  const tone = RISK_META[a.risk.level]?.tone ?? 'nodata';
  const finished = a.remaining_points_max === 0;
  return (
    <Card className="status-card" aria-labelledby="status-title">
      <div className="stack-sm">
        <h2 className="card-title" id="status-title">
          Текущая ситуация
        </h2>
        <span>
          <RiskBadge level={a.risk.level} label={a.risk.label} size="md" />
        </span>
        {a.risk.reasons.length > 0 && (
          <ul className="reasons">
            {a.risk.reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        )}
        {explanationRest(a) && <p className="small muted">{explanationRest(a)}</p>}
        {a.recommendation && (
          <p className="recommendation">
            <Lightbulb size={18} aria-hidden="true" />
            <span>{a.recommendation}</span>
          </p>
        )}
      </div>
      <div className="stack-sm">
        <div className="big-points">
          <span className="big-points__value num">{fmtNum(a.current_semester_points)}</span>
          <span className="muted num">
            из {fmtNum(a.semester_points_max)} {a.assessment_type === 'exam' ? 'семестровых' : ''}
          </span>
        </div>
        <PointsBar
          max={a.semester_points_max}
          earned={a.current_semester_points}
          remaining={a.remaining_points_max}
          missing={a.missing_points_max}
          tone={tone}
          marks={marksFor(a)}
          legend
        />
        <dl className="dl small">
          <div className="dl__row">
            <dt>Максимум за завершённые модули</dt>
            <dd className="num">{fmtNum(a.completed_points_max)}</dd>
          </div>
          <div className="dl__row">
            <dt>Ещё можно набрать</dt>
            <dd className="num">{fmtNum(a.remaining_points_max)}</dd>
          </div>
          {a.missing_points_max > 0 && (
            <div className="dl__row">
              <dt>Баллы не внесены</dt>
              <dd className="num">{fmtNum(a.missing_points_max)}</dd>
            </div>
          )}
          <div className="dl__row">
            <dt>{a.assessment_type === 'exam' ? 'Нужно в семестре, чтобы хватило 18 на экзамене' : 'Порог сдачи'}</dt>
            <dd className="num">{fmtNum(a.assessment_type === 'exam' ? a.semester_target : a.passing_threshold)}</dd>
          </div>
          {a.pace_is_reliable && a.current_pace != null && (
            <div className="dl__row">
              <dt>Текущий темп (доля от возможного)</dt>
              <dd className="num">{fmtPercent(a.current_pace)}</dd>
            </div>
          )}
          {a.projected_semester_points != null && !finished && (
            <div className="dl__row">
              <dt>Ориентир при сохранении темпа</dt>
              <dd className="num">≈ {Math.round(a.projected_semester_points)}</dd>
            </div>
          )}
          {finished && a.current_grade && (
            <div className="dl__row">
              <dt>Оценка по итогам семестра</dt>
              <dd className="strong">{a.current_grade.label}</dd>
            </div>
          )}
        </dl>
        {a.data_issues.length > 0 && (
          <Callout tone="nodata" icon={<AlertTriangle size={18} />} title="Данные неполные">
            <ul className="small" style={{ margin: 0, paddingLeft: 18 }}>
              {a.data_issues.map((x) => (
                <li key={x}>{x}</li>
              ))}
            </ul>
          </Callout>
        )}
      </div>
    </Card>
  );
}

function TargetsBlock({ a }: { a: DisciplineAnalytics }) {
  return (
    <Card aria-labelledby="targets-title">
      <CardHeader id="targets-title" title={a.assessment_type === 'credit' ? 'Получение зачёта' : 'Достижимость оценок'} level={2} />
      <div className={`target-list ${a.targets.length >= 3 ? 'target-list--3' : ''}`}>
        {a.targets.map((t) => {
          const need = targetNeed(t, a);
          return (
            <div key={t.threshold} className="target">
              <div className="target__head">
                <span className="target__name">
                  {t.label} <span className="muted num">· {fmtNum(t.threshold)}</span>
                </span>
                <TargetBadge status={t.status} />
              </div>
              {need && <p className="target__need strong small">{need}</p>}
              <p className="target__text small muted">{t.explanation}</p>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

function ExamBlock({ a }: { a: DisciplineAnalytics }) {
  const e = a.exam;
  if (!e) return null;
  const pos = (v: number) => `${Math.max(0, Math.min(100, v))}%`;
  const lo = e.result != null ? (e.final_total ?? a.current_semester_points + e.result) : e.total_at_exam_min;
  const hi = e.result != null ? lo : e.total_at_exam_max;
  return (
    <Card className="exam-box" aria-labelledby="exam-title">
      <CardHeader id="exam-title" title="Семестр + экзамен" icon={<GraduationCap className="card-icon" aria-hidden="true" />} />
      <div className="exam-min">
        <span className="exam-min__num num" aria-hidden="true">
          18
        </span>
        <p className="small">
          <strong>Обязательный минимум на экзамене — 18 из 30.</strong> Без него экзамен не сдан, даже если сумма с семестром
          достигает 60. Итог = семестр (до 70) + экзамен (до 30).
        </p>
      </div>
      {e.result != null ? (
        <p>
          Экзамен сдан на <strong className="num">{fmtNum(e.result)}</strong> — итог{' '}
          <strong className="num">{fmtNum(lo)}</strong> из 100.
        </p>
      ) : (
        <p className="small">
          С текущими {fmtNum(a.current_semester_points)} семестровыми баллами итог будет от{' '}
          <strong className="num">{fmtNum(e.total_at_exam_min)}</strong> (экзамен на 18) до{' '}
          <strong className="num">{fmtNum(e.total_at_exam_max)}</strong> (на 30).
          {e.total_max_possible != null && e.total_max_possible > e.total_at_exam_max && (
            <> Если добрать все оставшиеся семестровые баллы — до {fmtNum(e.total_max_possible)}.</>
          )}
        </p>
      )}
      <div className="corridor" role="img" aria-label={`Возможный итог от ${fmtNum(lo)} до ${fmtNum(hi)} из 100; пороги 60, 71 и 85`}>
        <div className="corridor__track">
          <div className="corridor__band" style={{ left: pos(lo), width: `calc(${pos(hi)} - ${pos(lo)})` }} />
        </div>
        {[60, 71, 85].map((g) => (
          <span key={g}>
            <span className="corridor__grade" style={{ left: pos(g) }} />
            <span className="corridor__grade-label num" style={{ left: pos(g) }}>
              {g}
            </span>
          </span>
        ))}
        <span className="corridor__end num" style={{ left: pos(lo) }}>
          {fmtNum(lo)}
        </span>
        {hi !== lo && (
          <span className="corridor__end num" style={{ left: pos(hi) }}>
            {fmtNum(hi)}
          </span>
        )}
      </div>
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
          {itemKindLabel(it.kind)}
          {it.due_date && (
            <>
              {' '}
              · срок {formatDay(it.due_date)}
              {overdue && <span className="strong"> · срок прошёл, баллы ещё не выставлены</span>}
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
  const fillMax = () => setValues(Object.fromEntries(pending.map((i) => [i.id, String(i.max_points)])));
  const r = sim.data?.analytics;
  const serverError = sim.error instanceof ApiError ? sim.error.message : sim.error ? 'Не удалось пересчитать. Попробуйте ещё раз.' : null;

  return (
    <Card className="whatif" aria-labelledby="whatif-title">
      <CardHeader id="whatif-title" title="Что если?" icon={<FlaskConical className="card-icon" aria-hidden="true" />} />
      <p className="small muted">
        Введите баллы, которые рассчитываете получить за предстоящие работы, — система пересчитает риск и цели.{' '}
        <strong>Это моделирование: ничего не сохраняется и не отправляется преподавателю.</strong>
      </p>
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
          {pending.length > 0 && (
            <Button type="button" variant="ghost" onClick={fillMax}>
              Заполнить максимумом
            </Button>
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
        <div className="compare" aria-live="polite">
          <div className="compare__col">
            <span className="compare__title">Сейчас</span>
            <div className="compare__row">
              <span>Риск</span>
              <RiskBadge level={a.risk.level} label={a.risk.label} />
            </div>
            <div className="compare__row">
              <span>Семестровые баллы</span>
              <span className="num">{fmtNum(a.current_semester_points)}</span>
            </div>
            {a.targets.map((t) => (
              <div key={t.threshold} className="compare__row">
                <span>{t.label}</span>
                <TargetBadge status={t.status} />
              </div>
            ))}
          </div>
          <div className="compare__col compare__col--sim">
            <span className="compare__title">Если всё получится</span>
            <div className="compare__row">
              <span>Риск</span>
              <RiskBadge level={r.risk.level} label={r.risk.label} />
            </div>
            <div className="compare__row">
              <span>Семестровые баллы</span>
              <span className="num strong">{fmtNum(r.current_semester_points)}</span>
            </div>
            {r.targets.map((t) => (
              <div key={t.threshold} className="compare__row">
                <span>{t.label}</span>
                <TargetBadge status={t.status} />
              </div>
            ))}
            {r.exam?.final_total != null && (
              <div className="compare__row">
                <span>Итог с экзаменом</span>
                <span className="num strong">{fmtNum(r.exam.final_total)}</span>
              </div>
            )}
            <p className="xsmall muted">{r.explanation}</p>
          </div>
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
      {a.risk.level === 'critical' && (
        <Callout tone="critical" icon={<AlertTriangle size={18} />} title="Что можно сделать сейчас">
          Обсудите ситуацию с преподавателем на ближайшем занятии или консультации. Если были уважительные причины пропусков —
          подайте <Link to="/applications/new?type=individual_schedule">заявление на индивидуальный график</Link>.
        </Callout>
      )}
      <div className="grid-2">
        <div className="col stack">
          {a.exam && <ExamBlock a={a} />}
          <TargetsBlock a={a} />
          <ModulesBlock a={a} />
          <WhatIf detail={detail} />
        </div>
        <div className="col stack">
          <TopicsBlock detail={detail} />
          <SideInfo detail={detail} />
        </div>
      </div>
      <p className="xsmall muted">
        Расчёт ориентировочный и обновляется после выставления новых баллов. Уровень риска — не вероятность и не официальная оценка.
      </p>
    </div>
  );
}
