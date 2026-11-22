import { Link, useSearchParams } from 'react-router-dom';
import { ChevronRight, Inbox } from 'lucide-react';
import { useStaffApplications } from '../../api/hooks';
import type { StaffApplicationFilter } from '../../api/types';
import { StatusPill } from '../../components/ui/Badge';
import { Card } from '../../components/ui/Card';
import { PageHeader } from '../../components/ui/PageHeader';
import { Segmented } from '../../components/ui/Segmented';
import { EmptyState, ErrorState, SkeletonCard } from '../../components/ui/States';
import { formatDateTime } from '../../lib/format';

const FILTERS: { value: StaffApplicationFilter; label: string }[] = [
  { value: 'active', label: 'В работе' },
  { value: 'submitted', label: 'Новые' },
  { value: 'needs_info', label: 'Ждут студента' },
  { value: 'ready', label: 'Готовы' },
  { value: 'closed', label: 'Закрытые' },
  { value: 'all', label: 'Все' },
];

export default function StaffQueuePage() {
  const [params, setParams] = useSearchParams();
  const raw = params.get('status') as StaffApplicationFilter | null;
  const filter: StaffApplicationFilter = raw && FILTERS.some((f) => f.value === raw) ? raw : 'active';
  const q = useStaffApplications(filter);
  const c = q.data?.counts ?? {};
  const counts: Partial<Record<StaffApplicationFilter, number>> = {
    submitted: c.submitted,
    needs_info: c.needs_info,
    ready: c.ready,
    active: (c.submitted ?? 0) + (c.in_progress ?? 0) + (c.needs_info ?? 0) + (c.approved ?? 0) + (c.ready ?? 0),
  };
  return (
    <div className="stack">
      <PageHeader title="Заявки студентов" subtitle="Очередь обработки деканата">
        <Segmented
          options={FILTERS.map((f) => ({ ...f, count: counts[f.value] || undefined }))}
          value={filter}
          onChange={(v) => setParams(v === 'active' ? {} : { status: v }, { replace: true })}
          label="Фильтр по статусу"
        />
      </PageHeader>
      <Card flush>
        {q.isPending ? (
          <div className="stack-sm" style={{ padding: 16 }}>
            <SkeletonCard lines={2} />
            <SkeletonCard lines={2} />
          </div>
        ) : q.isError ? (
          <ErrorState error={q.error} onRetry={() => void q.refetch()} retrying={q.isFetching} />
        ) : q.data.items.length === 0 ? (
          <EmptyState icon={<Inbox />} title="Заявок нет" text="В этой категории сейчас пусто." />
        ) : (
          <ul className="list">
            {q.data.items.map((a) => (
              <li key={a.id}>
                <Link to={`/staff/applications/${a.id}`} className={`list-row app-row ${a.status === 'submitted' ? 'app-row--attention' : ''}`}>
                  <span className="list-row__body">
                    <span className="list-row__title">{a.title}</span>
                    <span className="list-row__meta">
                      {a.student ? `${a.student.full_name} · ${a.student.group}` : 'студент'} · № <span className="num">{a.number}</span>
                    </span>
                    {a.summary && <span className="list-row__meta app-row__summary">{a.summary}</span>}
                    <span className="row-wrap" style={{ marginTop: 6 }}>
                      <StatusPill status={a.status} label={a.status_label} />
                      <span className="xsmall muted num">обновлено {formatDateTime(a.updated_at)}</span>
                    </span>
                  </span>
                  <ChevronRight size={18} aria-hidden="true" />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
