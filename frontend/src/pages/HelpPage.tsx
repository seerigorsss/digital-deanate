import { useMemo, useState } from 'react';
import { ChevronDown, MessageCircleQuestion, Search } from 'lucide-react';
import { useFaq, useMeta } from '../api/hooks';
import { useAuth } from '../auth/AuthContext';
import { ButtonLink } from '../components/ui/Button';
import { Callout } from '../components/ui/Callout';
import { Card } from '../components/ui/Card';
import { PageHeader } from '../components/ui/PageHeader';
import { ErrorState, NoResults, PageSkeleton } from '../components/ui/States';

export default function HelpPage() {
  const q = useFaq();
  const meta = useMeta();
  const { user } = useAuth();
  const [query, setQuery] = useState('');
  const items = useMemo(() => {
    const all = q.data?.items ?? [];
    const s = query.trim().toLowerCase();
    return s ? all.filter((f) => (f.question + ' ' + f.answer).toLowerCase().includes(s)) : all;
  }, [q.data, query]);
  const cats = [...new Set(items.map((f) => f.category))];

  return (
    <div className="stack">
      <PageHeader title="Помощь" subtitle="Ответы на частые вопросы" />
      <label className="search-box">
        <Search size={18} aria-hidden="true" />
        <span className="sr-only">Поиск по вопросам</span>
        <input className="input" type="search" placeholder="Например: справка, экзамен, статус" value={query} onChange={(e) => setQuery(e.target.value)} />
      </label>
      {q.isPending ? (
        <PageSkeleton cards={2} />
      ) : q.isError ? (
        <Card>
          <ErrorState error={q.error} onRetry={() => void q.refetch()} retrying={q.isFetching} />
        </Card>
      ) : items.length === 0 ? (
        <Card>
          <NoResults text="Ничего не нашлось — попробуйте другое слово или напишите в деканат." onReset={() => setQuery('')} />
        </Card>
      ) : (
        cats.map((c) => (
          <Card key={c} aria-label={c}>
            <h2 className="section-title">{c}</h2>
            {items
              .filter((f) => f.category === c)
              .map((f) => (
                <details key={f.id} className="accordion faq-item">
                  <summary>
                    <span className="strong">{f.question}</span>
                    <ChevronDown className="accordion__chevron" size={18} aria-hidden="true" />
                  </summary>
                  <div className="accordion__body faq-answer stack-sm">
                    <p className="small">{f.answer}</p>
                    {f.link && user?.role === 'student' && (
                      <ButtonLink to={f.link} size="sm">
                        Перейти
                      </ButtonLink>
                    )}
                  </div>
                </details>
              ))}
          </Card>
        ))
      )}
      {user?.role === 'student' && (
        <Card soft>
          <div className="row-wrap" style={{ justifyContent: 'space-between' }}>
            <span className="small">Не нашли ответ?</span>
            <ButtonLink to="/applications/new?type=dean_question" variant="primary" icon={<MessageCircleQuestion size={18} />}>
              Написать в деканат
            </ButtonLink>
          </div>
        </Card>
      )}
      {meta.data && <Callout tone="nodata">{meta.data.disclaimer}</Callout>}
    </div>
  );
}
