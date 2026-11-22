import { useParams } from 'react-router-dom';
import { BadgeCheck, BookMarked, Clock, ExternalLink, Globe } from 'lucide-react';
import { useTopic } from '../api/hooks';
import type { Resource } from '../api/types';
import { ButtonLink } from '../components/ui/Button';
import { Callout } from '../components/ui/Callout';
import { Card } from '../components/ui/Card';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState, ErrorState, PageSkeleton } from '../components/ui/States';
import { formatDate } from '../lib/format';
import { resourceIcon } from '../lib/semantics';

const DIFFICULTY: Record<string, string> = { basic: 'Базовый уровень', intermediate: 'Средний уровень', advanced: 'Продвинутый уровень' };

function ResourceCard({ r }: { r: Resource }) {
  const Icon = resourceIcon(r.type);
  return (
    <Card as="article" className="resource" aria-labelledby={`res-${r.id}`}>
      <div className="resource__head">
        <span className="badge badge--sm tone-accent">
          <Icon size={14} aria-hidden="true" /> {r.type_label}
        </span>
        {r.language && r.language !== 'ru' && (
          <span className="badge badge--sm tone-nodata">
            <Globe size={14} aria-hidden="true" /> {r.language === 'en' ? 'на английском' : r.language}
          </span>
        )}
        {r.difficulty && DIFFICULTY[r.difficulty] && <span className="badge badge--sm tone-nodata">{DIFFICULTY[r.difficulty]}</span>}
        {r.duration_minutes != null && (
          <span className="badge badge--sm tone-nodata">
            <Clock size={14} aria-hidden="true" /> ~{r.duration_minutes} мин
          </span>
        )}
      </div>
      <h2 className="resource__title" id={`res-${r.id}`}>
        {r.title}
      </h2>
      <p className="xsmall muted">{[r.source, r.author].filter(Boolean).join(' · ')}</p>
      {r.summary && <p className="small">{r.summary}</p>}
      {r.relevance && (
        <p className="resource__why small">
          <strong>Почему рекомендовано:</strong> {r.relevance}
        </p>
      )}
      <div className="row-wrap" style={{ justifyContent: 'space-between' }}>
        <span className="xsmall muted">
          {r.link_status === 'verified' ? (
            <>
              <BadgeCheck size={14} aria-hidden="true" /> Ссылка проверена{r.checked_on ? ` ${formatDate(r.checked_on)}` : ''}
            </>
          ) : (
            'Ссылка не проверена'
          )}
          {r.access_note ? ` · ${r.access_note}` : ''}
        </span>
        <a className="btn btn--secondary btn--md" href={r.url} target="_blank" rel="noopener noreferrer">
          Открыть <ExternalLink size={16} aria-hidden="true" />
          <span className="sr-only"> (откроется в новой вкладке)</span>
        </a>
      </div>
    </Card>
  );
}

export default function TopicPage() {
  const { disciplineId, topicId } = useParams();
  const tid = Number(topicId);
  const q = useTopic(tid);
  const back = { to: `/study/${disciplineId ?? ''}`, label: 'К дисциплине' };

  if (q.isPending) return <PageSkeleton cards={3} />;
  if (q.isError)
    return (
      <div className="stack">
        <PageHeader title="Тема" back={back} />
        <Card>
          <ErrorState error={q.error} onRetry={() => void q.refetch()} retrying={q.isFetching} />
        </Card>
      </div>
    );
  const t = q.data;
  return (
    <div className="stack">
      <PageHeader
        title={t.topic.title}
        back={{ to: `/study/${t.discipline.id}`, label: t.discipline.title }}
        subtitle={t.module ? `Модуль ${t.module.ordinal}. ${t.module.title}` : t.discipline.title}
      />
      {t.topic.is_weak && (
        <Callout tone="medium" icon={<BookMarked size={18} />} title="Стоит повторить">
          По работам этого модуля набрано меньше 60% возможных баллов. Материалы ниже помогут закрыть пробелы до следующего контроля.
        </Callout>
      )}
      {t.resources.length === 0 ? (
        <Card>
          <EmptyState
            icon={<BookMarked />}
            title="Материалы по этой теме пока не подобраны"
            text="Мы показываем только проверенные открытые источники. Спросите преподавателя о рекомендуемой литературе."
            actions={<ButtonLink to={`/study/${t.discipline.id}`}>Вернуться к дисциплине</ButtonLink>}
          />
        </Card>
      ) : (
        <>
          <p className="small muted">
            Подборка открытых материалов именно по этой теме: {t.resources.length}. Ссылки ведут на внешние сайты и открываются в новой
            вкладке.
          </p>
          <div className="grid-cards">
            {t.resources.map((r) => (
              <ResourceCard key={r.id} r={r} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
