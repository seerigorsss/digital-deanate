import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { CheckCircle2, ChevronRight, Clock } from 'lucide-react';
import { useApplicationTypes, useCreateApplication } from '../api/hooks';
import { ApiError } from '../api/client';
import type { ApplicationDetail, ApplicationType, Payload } from '../api/types';
import { ApplicationForm, type FieldErrors } from '../components/domain/ApplicationForm';
import { ButtonLink } from '../components/ui/Button';
import { Callout } from '../components/ui/Callout';
import { Card } from '../components/ui/Card';
import { PageHeader } from '../components/ui/PageHeader';
import { ErrorState, PageSkeleton } from '../components/ui/States';
import { useToast } from '../components/ui/Toast';
import { plural } from '../lib/format';
import { applicationTypeIcon, CATEGORY_LABELS } from '../lib/semantics';

function TypePicker({ types, onPick }: { types: ApplicationType[]; onPick: (key: string) => void }) {
  const groups = ['certificate', 'statement', 'question'] as const;
  return (
    <div className="stack">
      {groups.map((g) => {
        const items = types.filter((t) => t.category === g);
        if (!items.length) return null;
        return (
          <section key={g} className="stack-sm" aria-labelledby={`grp-${g}`}>
            <h2 className="section-title" id={`grp-${g}`}>
              {CATEGORY_LABELS[g] ?? g}
            </h2>
            <div className="grid-cards">
              {items.map((t) => {
                const Icon = applicationTypeIcon(t.icon);
                return (
                  <button key={t.key} type="button" className="type-card" onClick={() => onPick(t.key)}>
                    <span className="list-row__icon tone-accent" aria-hidden="true">
                      <Icon size={20} />
                    </span>
                    <span className="type-card__body">
                      <span className="type-card__title">{t.title}</span>
                      <span className="small muted">{t.description}</span>
                      <span className="xsmall muted">
                        <Clock size={12} aria-hidden="true" /> обычно до {t.processing_days}{' '}
                        {plural(t.processing_days, ['рабочего дня', 'рабочих дней', 'рабочих дней'])}
                      </span>
                    </span>
                    <ChevronRight size={18} aria-hidden="true" />
                  </button>
                );
              })}
            </div>
          </section>
        );
      })}
    </div>
  );
}

function Success({ app }: { app: ApplicationDetail }) {
  const draft = app.status === 'draft';
  return (
    <Card>
      <div className="success-screen" role="status">
        <span className="success-screen__icon" aria-hidden="true">
          <CheckCircle2 />
        </span>
        <h2 className="card-title">{draft ? 'Черновик сохранён' : 'Заявка отправлена'}</h2>
        <p>
          «{app.title}» · № <span className="num strong">{app.number}</span>
        </p>
        <p className="small muted" style={{ maxWidth: 480 }}>
          {app.next_step}
        </p>
        <div className="row-wrap" style={{ justifyContent: 'center' }}>
          <ButtonLink to={`/applications/${app.id}`} variant="primary">
            Открыть заявку
          </ButtonLink>
          <ButtonLink to="/applications">Все заявки</ButtonLink>
        </div>
      </div>
    </Card>
  );
}

export default function NewApplicationPage() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const toast = useToast();
  const typesQ = useApplicationTypes();
  const create = useCreateApplication();
  const [busy, setBusy] = useState<'submit' | 'draft' | null>(null);
  const [serverErrors, setServerErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [created, setCreated] = useState<ApplicationDetail | null>(null);
  const typeKey = params.get('type');

  if (typesQ.isPending) return <PageSkeleton cards={3} />;
  if (typesQ.isError)
    return (
      <Card>
        <ErrorState error={typesQ.error} onRetry={() => void typesQ.refetch()} retrying={typesQ.isFetching} />
      </Card>
    );
  const types = typesQ.data.items;
  const type = types.find((t) => t.key === typeKey) ?? null;

  if (created) {
    return (
      <div className="stack">
        <PageHeader title="Новая заявка" back={{ to: '/applications', label: 'Заявки' }} />
        <Success app={created} />
      </div>
    );
  }

  const submit = (payload: Payload, doSubmit: boolean) => {
    if (!type) return;
    setBusy(doSubmit ? 'submit' : 'draft');
    setServerErrors({});
    setFormError(null);
    create.mutate(
      { type_key: type.key, payload, submit: doSubmit },
      {
        onSuccess: (app) => {
          setCreated(app);
          toast.success(doSubmit ? `Заявка № ${app.number} отправлена` : 'Черновик сохранён');
        },
        onError: (err) => {
          if (err instanceof ApiError && err.errors.length) setServerErrors(err.fieldErrors);
          setFormError(err instanceof ApiError ? err.message : 'Не удалось отправить заявку. Проверьте соединение и попробуйте снова.');
        },
        onSettled: () => setBusy(null),
      },
    );
  };

  return (
    <div className="stack">
      <PageHeader
        title={type ? type.title : 'Новая заявка'}
        back={type ? { to: '/applications/new', label: 'Выбор типа' } : { to: '/applications', label: 'Заявки' }}
        subtitle={type ? type.description : 'Выберите, какой документ нужен или с каким вопросом обратиться в деканат'}
      />
      {typeKey && !type && (
        <Callout tone="medium" role="alert">
          Такого типа заявки нет — выберите из списка ниже.
        </Callout>
      )}
      {!type ? (
        <TypePicker
          types={types}
          onPick={(key) => {
            setParams({ type: key });
            window.scrollTo({ top: 0 });
          }}
        />
      ) : (
        <Card>
          <div className="stack">
            <p className="xsmall muted">
              <Clock size={12} aria-hidden="true" /> Срок обработки — обычно до {type.processing_days}{' '}
              {plural(type.processing_days, ['рабочего дня', 'рабочих дней', 'рабочих дней'])}. Статус будет обновляться в разделе{' '}
              <Link to="/applications">«Заявки»</Link> и в уведомлениях.
            </p>
            {formError && (
              <Callout tone="critical" role="alert">
                {formError}
              </Callout>
            )}
            <ApplicationForm
              key={type.key}
              type={type}
              busy={busy}
              serverErrors={serverErrors}
              onSubmit={submit}
              onCancel={() => navigate('/applications/new')}
            />
          </div>
        </Card>
      )}
    </div>
  );
}
