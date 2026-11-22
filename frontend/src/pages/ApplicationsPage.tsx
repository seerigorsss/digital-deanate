import { useSearchParams } from 'react-router-dom';
import { FilePlus2, Inbox } from 'lucide-react';
import { useApplications } from '../api/hooks';
import type { ApplicationFilter } from '../api/types';
import { ApplicationRow } from '../components/domain/ApplicationRow';
import { ButtonLink } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { PageHeader } from '../components/ui/PageHeader';
import { Segmented } from '../components/ui/Segmented';
import { EmptyState, ErrorState, SkeletonCard } from '../components/ui/States';

const FILTERS: { value: ApplicationFilter; label: string }[] = [
  { value: 'active', label: 'Активные' },
  { value: 'draft', label: 'Черновики' },
  { value: 'closed', label: 'Завершённые' },
  { value: 'all', label: 'Все' },
];
const EMPTY: Record<ApplicationFilter, { title: string; text: string }> = {
  active: { title: 'Активных заявок нет', text: 'Закажите справку или напишите в деканат — статус будет виден здесь.' },
  draft: { title: 'Черновиков нет', text: 'Начатую, но не отправленную заявку можно сохранить как черновик.' },
  closed: { title: 'Завершённых заявок пока нет', text: 'Здесь появятся выданные, отклонённые и отозванные заявки.' },
  all: { title: 'Заявок пока нет', text: 'Справки, заявления и обращения в деканат оформляются онлайн.' },
};

export default function ApplicationsPage() {
  const [params, setParams] = useSearchParams();
  const raw = params.get('status') as ApplicationFilter | null;
  const filter: ApplicationFilter = raw && FILTERS.some((f) => f.value === raw) ? raw : 'active';
  const q = useApplications(filter);
  const counts = q.data?.counts;

  return (
    <div className="stack">
      <PageHeader
        title="Заявки"
        subtitle="Справки, заявления и обращения в деканат"
        actions={
          <ButtonLink to="/applications/new" variant="primary" icon={<FilePlus2 size={18} />}>
            Новая заявка
          </ButtonLink>
        }
      >
        <Segmented
          options={FILTERS.map((f) => ({ ...f, count: counts?.[f.value] }))}
          value={filter}
          onChange={(v) => setParams(v === 'active' ? {} : { status: v }, { replace: true })}
          label="Фильтр заявок"
          block
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
          <EmptyState
            icon={<Inbox />}
            title={EMPTY[filter].title}
            text={EMPTY[filter].text}
            actions={
              <ButtonLink to="/applications/new" variant="primary">
                Создать заявку
              </ButtonLink>
            }
          />
        ) : (
          <ul className="list" aria-busy={q.isFetching}>
            {q.data.items.map((a) => (
              <li key={a.id}>
                <ApplicationRow app={a} />
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
