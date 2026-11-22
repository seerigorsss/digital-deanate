import { useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { CalendarCheck, Radar, Sparkles } from 'lucide-react';
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
import { formatDate, formatDay, weekdayShort } from '../lib/format';

type Tab = 'radar' | 'session' | 'record';
const TABS: { value: Tab; label: string }[] = [
  { value: 'radar', label: 'Успеваемость' },
  { value: 'session', label: 'Сессия' },
  { value: 'record', label: 'Зачётная книжка' },
];

/** Короткая подсказка по итогам расчёта: одна фраза о темпе + какие предметы подтянуть, без лишних пояснений. */
function hintFor(a: AnalyticsSummary): { headline: string; pull: string[] } {
  const pull = a.disciplines.filter((d) => ['critical', 'high', 'medium'].includes(d.risk.level)).map((d) => d.title);
  const zone = a.index.value == null ? null : a.index.zone;
  const headline =
    zone === null
      ? 'Пока мало оценок, чтобы делать выводы — загляни сюда позже.'
      : zone === 'stable'
        ? 'Отлично! Ты идёшь в хорошем темпе.'
        : zone === 'medium'
          ? 'Неплохо, но кое-что стоит подтянуть.'
          : zone === 'high'
            ? 'Есть риск не закрыть часть предметов — самое время навёрстывать.'
            : 'Ситуация непростая, но её ещё можно исправить.';
  return { headline, pull };
}

function RadarTab({ a }: { a: AnalyticsSummary }) {
  const [filter, setFilter] = useState<RiskLevel | null>(null);
  const [hintOpen, setHintOpen] = useState(false);
  const list = useMemo(
    () => (filter ? a.disciplines.filter((d) => d.risk.level === filter) : a.disciplines),
    [a.disciplines, filter],
  );
  const idx = a.index;
  const hint = hintFor(a);
  return (
    <div className="stack">
      <Card className="radar-hero" aria-labelledby="index-title">
        <div className="radar-hero__gauge">
          <Gauge value={idx.value} zone={idx.zone} label={idx.label ?? undefined} />
        </div>
        <div className="stack-sm">
          <h2 className="card-title" id="index-title">
            Успеваемость
          </h2>
          <div className="row-wrap">
            {idx.value != null ? (
              <ZoneBadge zone={idx.zone} label={idx.label} size="md" />
            ) : (
              <RiskBadge level="insufficient_data" label="Недостаточно данных" size="md" />
            )}
          </div>
          <div>
            <button
              type="button"
              className="ai-hint-btn"
              aria-expanded={hintOpen}
              aria-controls="ai-hint"
              onClick={() => setHintOpen((v) => !v)}
            >
              <Sparkles size={18} aria-hidden="true" /> Подсказка ИИ
            </button>
          </div>
          {hintOpen && (
            <div className="ai-hint" id="ai-hint" role="status">
              <p className="strong">{hint.headline}</p>
              {hint.pull.length > 0 && (
                <p className="small">
                  Стоит подтянуть: {hint.pull.map((t) => `«${t}»`).join(', ')}.
                </p>
              )}
            </div>
          )}
        </div>
      </Card>

      <ZoneChips counts={a.zone_counts} active={filter} onSelect={setFilter} />

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
      <Card className="session-hero" aria-label="Даты сессии">
        <span className="session-hero__icon" aria-hidden="true">
          <CalendarCheck />
        </span>
        <div className="stack-xs">
          <span className="small muted">Экзаменационная сессия</span>
          <span className="session-hero__dates num">
            {formatDay(c.session_starts_on)} — {formatDate(c.session_ends_on)}
          </span>
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
              <span className="xsmall muted">{x.assessment_label}</span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

/** Порядок групп в зачётке: отлично → хорошо → удовлетворительно → зачтено → неудовлетворительно. */
const GRADE_ORDER: Record<string, number> = { excellent: 0, good: 1, satisfactory: 2, passed: 3, unsatisfactory: 4, failed: 4 };

const GRADE_CLASS: Record<string, string> = {
  excellent: 'grade--excellent',
  good: 'grade--good',
  satisfactory: 'grade--satisfactory',
  passed: 'grade--passed',
  unsatisfactory: 'grade--fail',
  failed: 'grade--fail',
};

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
        <div className="avg-row">
          <span className="small muted">Средний балл за всё время</span>
          <span className="avg-row__value num">{g.overall_average != null ? g.overall_average.toFixed(2).replace('.', ',') : '—'}</span>
        </div>
      </Card>
      {g.record_book.map((sem) => (
        <Card key={sem.semester} aria-labelledby={`sem-${sem.semester}`}>
          <CardHeader
            id={`sem-${sem.semester}`}
            title={`${sem.semester}-й семестр`}
            aside={sem.average != null ? <span className="small muted num">средний {sem.average.toFixed(2).replace('.', ',')}</span> : undefined}
          />
          <ul className="record-list">
            {[...sem.entries].sort((x, y) => (GRADE_ORDER[x.grade_key] ?? 9) - (GRADE_ORDER[y.grade_key] ?? 9)).map((e) => (
              <li key={e.id} className="record-row">
                <span className="record-row__body">
                  <span className="record-row__title">{e.discipline_title}</span>
                  <span className="xsmall muted">{e.assessment_label}</span>
                </span>
                <span className={`grade ${GRADE_CLASS[e.grade_key] ?? ''}`}>{e.grade_label}</span>
              </li>
            ))}
          </ul>
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
      <PageHeader title="Учёба" docTitle={TABS.find((t) => t.value === tab)?.label} subtitle="Успеваемость, сессия и зачётная книжка">
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
