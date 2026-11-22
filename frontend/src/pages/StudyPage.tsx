import { useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Award, CalendarCheck, ChevronRight, Info, Radar, Sparkles, Target as TargetIcon } from 'lucide-react';
import { useAnalytics, useGrades } from '../api/hooks';
import type { AnalyticsSummary, GradesResponse, RiskLevel } from '../api/types';
import { DisciplineRow } from '../components/domain/DisciplineRow';
import { ZoneChips } from '../components/domain/ZoneChips';
import { RiskBadge, ZoneBadge } from '../components/ui/Badge';
import { Card, CardHeader } from '../components/ui/Card';
import { Gauge } from '../components/ui/Gauge';
import { PageHeader } from '../components/ui/PageHeader';
import { Segmented } from '../components/ui/Segmented';
import { EmptyState, ErrorState, NoResults, PageSkeleton } from '../components/ui/States';
import { daysLeftLabel, daysBetween, fmtNum, formatDate, formatDay, weekdayShort } from '../lib/format';

type Tab = 'radar' | 'session' | 'record';
const TABS: { value: Tab; label: string }[] = [
  { value: 'radar', label: 'Радар' },
  { value: 'session', label: 'Сессия' },
  { value: 'record', label: 'Зачётная книжка' },
];

function RadarTab({ a }: { a: AnalyticsSummary }) {
  const [filter, setFilter] = useState<RiskLevel | null>(null);
  const list = useMemo(
    () => (filter ? a.disciplines.filter((d) => d.risk.level === filter) : a.disciplines),
    [a.disciplines, filter],
  );
  const idx = a.index;
  const capped = idx.caps_applied.length > 0 && idx.uncapped_value != null && idx.uncapped_value !== idx.value;
  return (
    <div className="stack">
      <Card className="radar-hero" aria-labelledby="index-title">
        <div className="radar-hero__gauge">
          <Gauge value={idx.value} zone={idx.zone} label={idx.label ?? undefined} />
        </div>
        <div className="stack-sm">
          <h2 className="card-title" id="index-title">
            Индекс учебной устойчивости
          </h2>
          <div className="row-wrap">
            {idx.value != null ? (
              <ZoneBadge zone={idx.zone} label={idx.label} />
            ) : (
              <RiskBadge level="insufficient_data" label="Недостаточно данных" />
            )}
            <span className="xsmall muted">ориентировочный показатель, не вероятность сдачи</span>
          </div>
          <p>{a.explanation}</p>
          <details className="disclosure">
            <summary>
              <Info size={16} aria-hidden="true" /> Как считается индекс
            </summary>
            <div className="disclosure__content small muted stack-sm">
              <p>{idx.formula}</p>
              {capped && (
                <p>
                  Без ограничения среднее было бы {fmtNum(idx.uncapped_value)}, но при дисциплинах в зоне{' '}
                  {idx.caps_applied.includes('critical') ? 'критического' : 'высокого'} риска индекс не может быть выше — чтобы
                  проблемный предмет не терялся среди благополучных.
                </p>
              )}
              {idx.disciplines_counted != null && <p>Учтено дисциплин: {idx.disciplines_counted}.</p>}
            </div>
          </details>
        </div>
      </Card>

      <ZoneChips counts={a.zone_counts} active={filter} onSelect={setFilter} />

      <div className="grid-2">
        <Card aria-labelledby="prio-title">
          <CardHeader id="prio-title" title="Что подтянуть в первую очередь" icon={<TargetIcon className="card-icon" aria-hidden="true" />} />
          {a.priorities.length === 0 ? (
            <EmptyState compact icon={<Sparkles />} title="Срочных задач нет" text="Все дисциплины в стабильной зоне — так держать." />
          ) : (
            <ol className="stack-sm" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
              {a.priorities.slice(0, 5).map((p, i) => (
                <li key={p.discipline_id}>
                  <Link to={`/study/${p.discipline_id}`} className="priority">
                    <span className="priority__num num" aria-hidden="true">
                      {i + 1}
                    </span>
                    <span className="priority__body">
                      <span className="row-wrap">
                        <span className="priority__title">{p.title}</span>
                        <RiskBadge level={p.risk_level} label={p.risk_label} />
                      </span>
                      <span className="priority__line">{p.reason}</span>
                      <span className="priority__line strong">{p.action}</span>
                      {p.deadline && (
                        <span className="priority__line xsmall muted">
                          <CalendarCheck size={14} aria-hidden="true" /> Срок: {weekdayShort(p.deadline)}, {formatDay(p.deadline)} (
                          {daysLeftLabel(daysBetween(a.as_of ?? p.deadline, p.deadline))})
                        </span>
                      )}
                    </span>
                    <ChevronRight size={18} aria-hidden="true" />
                  </Link>
                </li>
              ))}
            </ol>
          )}
        </Card>
        <Card aria-labelledby="pos-title">
          <CardHeader id="pos-title" title="Что идёт хорошо" icon={<Award className="card-icon" aria-hidden="true" />} />
          {a.positives.length === 0 ? (
            <EmptyState compact title="Пока без отметок" text="Когда по дисциплине будет обеспечен порог или хороший запас, она появится здесь." />
          ) : (
            <ul className="stack-sm" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
              {a.positives.map((p) => (
                <li key={p.discipline_id}>
                  <Link to={`/study/${p.discipline_id}`} className="positive">
                    <span className="strong">{p.title}</span>
                    <span className="small muted">{p.message}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card aria-labelledby="disc-title">
        <CardHeader
          id="disc-title"
          title={filter ? `Дисциплины: ${a.disciplines.find((d) => d.risk.level === filter)?.risk.label ?? ''}` : 'Все дисциплины семестра'}
          icon={<Radar className="card-icon" aria-hidden="true" />}
        />
        {list.length === 0 ? (
          <NoResults text="Нет дисциплин с таким уровнем риска." onReset={() => setFilter(null)} />
        ) : (
          <div className="disc-list">
            {list.map((d) => (
              <DisciplineRow key={d.discipline_id} d={d} />
            ))}
          </div>
        )}
        <p className="xsmall muted" style={{ marginTop: 12 }}>
          Уровень риска — эвристика по набранным баллам, оставшемуся потенциалу и темпу, а не вероятность. Расчёт обновляется
          сразу после выставления новых баллов.
        </p>
      </Card>
    </div>
  );
}

function SessionTab({ g }: { g: GradesResponse }) {
  const c = g.current;
  const exams = c.attestations.filter((x) => x.assessment_type === 'exam');
  const others = c.attestations.filter((x) => x.assessment_type !== 'exam');
  return (
    <div className="stack">
      <Card>
        <CardHeader title={c.period_title} icon={<CalendarCheck className="card-icon" aria-hidden="true" />} />
        <div className="stats">
          <div className="stat">
            <span className="stat__label">Экзаменационная сессия</span>
            <span className="stat__value num">
              {formatDay(c.session_starts_on)} — {formatDate(c.session_ends_on)}
            </span>
          </div>
          <div className="stat">
            <span className="stat__label">Экзаменов</span>
            <span className="stat__value num">{exams.length}</span>
          </div>
          <div className="stat">
            <span className="stat__label">Зачётных единиц в семестре</span>
            <span className="stat__value num">{c.credits_total}</span>
          </div>
        </div>
      </Card>
      <Card aria-labelledby="exams-title">
        <CardHeader id="exams-title" title="Экзамены" level={2} />
        {exams.length === 0 ? (
          <EmptyState compact title="Экзаменов в этом семестре нет" />
        ) : (
          <div className="table-wrap">
            <table className="table table--responsive">
              <thead>
                <tr>
                  <th scope="col">Дисциплина</th>
                  <th scope="col">Дата</th>
                  <th scope="col">Аудитория</th>
                </tr>
              </thead>
              <tbody>
                {exams.map((x) => (
                  <tr key={x.discipline_id}>
                    <td className="table__primary" data-label="Дисциплина">
                      <Link to={`/study/${x.discipline_id}`}>{x.title}</Link>
                    </td>
                    <td data-label="Дата" className="num">
                      {x.exam_date ? `${weekdayShort(x.exam_date)}, ${formatDate(x.exam_date)}` : 'уточняется'}
                    </td>
                    <td data-label="Аудитория">{x.exam_room ?? 'уточняется'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="xsmall muted" style={{ marginTop: 12 }}>
          На экзамене нужно набрать не меньше 18 баллов из 30 — иначе экзамен не сдан, даже если сумма с семестром достигает 60.
        </p>
      </Card>
      <Card aria-labelledby="credits-title">
        <CardHeader id="credits-title" title="Зачёты и распределённые экзамены" level={2} />
        <ul className="stack-sm" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
          {others.map((x) => (
            <li key={x.discipline_id} className="row-wrap" style={{ justifyContent: 'space-between' }}>
              <Link to={`/study/${x.discipline_id}`}>{x.title}</Link>
              <span className="xsmall muted">{x.assessment_label} · итог по баллам семестра</span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

function RecordTab({ g }: { g: GradesResponse }) {
  if (g.record_book.length === 0)
    return (
      <Card>
        <EmptyState title="Записей пока нет" text="Итоговые оценки появятся после первой сессии." />
      </Card>
    );
  return (
    <div className="stack">
      <Card soft>
        <div className="stats">
          <div className="stat">
            <span className="stat__label">Средний балл за всё время</span>
            <span className="stat__value num">{g.overall_average != null ? g.overall_average.toFixed(2).replace('.', ',') : '—'}</span>
            <span className="stat__hint">по экзаменам и дифференцированным оценкам, шкала 5</span>
          </div>
          <div className="stat">
            <span className="stat__label">Завершено семестров</span>
            <span className="stat__value num">{g.record_book.length}</span>
          </div>
        </div>
      </Card>
      {g.record_book.map((sem) => (
        <Card key={sem.semester} aria-labelledby={`sem-${sem.semester}`}>
          <CardHeader
            id={`sem-${sem.semester}`}
            title={`${sem.semester}-й семестр`}
            aside={sem.average != null ? <span className="small muted num">средний балл {sem.average.toFixed(2).replace('.', ',')}</span> : undefined}
          />
          <div className="table-wrap">
            <table className="table table--responsive">
              <thead>
                <tr>
                  <th scope="col">Дисциплина</th>
                  <th scope="col">Форма</th>
                  <th scope="col" className="num-cell">Баллы</th>
                  <th scope="col">Оценка</th>
                  <th scope="col" className="num-cell">ЗЕ</th>
                </tr>
              </thead>
              <tbody>
                {sem.entries.map((e) => (
                  <tr key={e.id}>
                    <td className="table__primary" data-label="Дисциплина">
                      {e.discipline_title}
                    </td>
                    <td data-label="Форма">{e.assessment_label}</td>
                    <td data-label="Баллы" className="num-cell num">
                      {e.points != null ? fmtNum(e.points) : '—'}
                    </td>
                    <td data-label="Оценка" className="strong">
                      {e.grade_label}
                    </td>
                    <td data-label="ЗЕ" className="num-cell num">
                      {e.credits ?? '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ))}
    </div>
  );
}

export default function StudyPage() {
  const [params, setParams] = useSearchParams();
  const raw = params.get('tab');
  const tab: Tab = raw === 'session' || raw === 'record' ? raw : 'radar';
  const analytics = useAnalytics();
  const grades = useGrades(tab !== 'radar');

  const setTab = (t: Tab) => {
    const next = new URLSearchParams(params);
    if (t === 'radar') next.delete('tab');
    else next.set('tab', t);
    setParams(next, { replace: true });
  };

  const q = tab === 'radar' ? analytics : grades;
  return (
    <div className="stack">
      <PageHeader title="Учёба" docTitle={tab === 'radar' ? 'Академический радар' : TABS.find((t) => t.value === tab)?.label} subtitle="Успеваемость, сессия и зачётная книжка">
        <Segmented options={TABS} value={tab} onChange={setTab} label="Разделы учёбы" mode="tabs" controls="study-panel" block />
      </PageHeader>
      <div id="study-panel" role="tabpanel" aria-label={TABS.find((t) => t.value === tab)?.label}>
        {q.isPending ? (
          <PageSkeleton cards={3} />
        ) : q.isError ? (
          <Card>
            <ErrorState error={q.error} onRetry={() => void q.refetch()} retrying={q.isFetching} />
          </Card>
        ) : tab === 'radar' && analytics.data ? (
          <RadarTab a={analytics.data} />
        ) : tab === 'session' && grades.data ? (
          <SessionTab g={grades.data} />
        ) : grades.data ? (
          <RecordTab g={grades.data} />
        ) : null}
      </div>
    </div>
  );
}
