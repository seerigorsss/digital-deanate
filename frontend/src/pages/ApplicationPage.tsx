import { useState, type FormEvent } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowRightCircle, FileText, MessageSquareReply, Send, Trash2, Undo2 } from 'lucide-react';
import { useApplication, useApplicationAction, useApplicationTypes, useDeleteDraft, useSendMessage, useUpdateDraft } from '../api/hooks';
import { ApiError } from '../api/client';
import type { ApplicationDetail, ApplicationMessage, HistoryEntry, Payload } from '../api/types';
import { ApplicationForm, type FieldErrors } from '../components/domain/ApplicationForm';
import { StatusPill } from '../components/ui/Badge';
import { Button, ButtonLink } from '../components/ui/Button';
import { Callout } from '../components/ui/Callout';
import { Card, CardHeader } from '../components/ui/Card';
import { TextAreaField } from '../components/ui/Field';
import { Modal } from '../components/ui/Modal';
import { PageHeader } from '../components/ui/PageHeader';
import { ErrorState, PageSkeleton } from '../components/ui/States';
import { useToast } from '../components/ui/Toast';
import { formatDateTime } from '../lib/format';
import { STATUS_META } from '../lib/semantics';

export function Timeline({ items, viewer = 'student' }: { items: HistoryEntry[]; viewer?: 'student' | 'staff' }) {
  return (
    <ol className="timeline">
      {[...items].reverse().map((h) => (
        <li key={h.id} className="timeline__item">
          <span className="row-wrap">
            <StatusPill status={h.to_status} label={h.to_label} />
            <span className="xsmall muted num">{formatDateTime(h.created_at)}</span>
            <span className="xsmall muted">{h.actor_role === 'staff' ? (viewer === 'staff' ? 'сотрудник деканата' : 'деканат') : h.actor_role === 'student' ? (viewer === 'student' ? 'вы' : 'студент') : 'система'}</span>
          </span>
          {h.comment && <p className="timeline__comment small">{h.comment}</p>}
        </li>
      ))}
    </ol>
  );
}

export function Chat({ messages, emptyText }: { messages: ApplicationMessage[]; emptyText: string }) {
  if (!messages.length) return <p className="small muted">{emptyText}</p>;
  return (
    <ul className="chat" aria-label="Переписка">
      {messages.map((m) => (
        <li key={m.id} className={`msg ${m.is_mine ? 'msg--mine' : ''}`}>
          <div className="msg__bubble">{m.text}</div>
          <span className="msg__meta xsmall muted">
            {m.is_mine ? 'Вы' : m.author_name} · {formatDateTime(m.created_at)}
          </span>
        </li>
      ))}
    </ul>
  );
}

export function ReplyForm({ busy, onSend, needsInfo }: { busy: boolean; onSend: (text: string, done: () => void) => void; needsInfo?: boolean }) {
  const [text, setText] = useState('');
  const [error, setError] = useState<string | null>(null);
  const submit = (e: FormEvent) => {
    e.preventDefault();
    const t = text.trim();
    if (!t) {
      setError('Напишите сообщение');
      return;
    }
    setError(null);
    onSend(t, () => setText(''));
  };
  return (
    <form onSubmit={submit} className="stack-sm" noValidate>
      <TextAreaField
        label={needsInfo ? 'Ваш ответ деканату' : 'Сообщение'}
        name="reply"
        rows={3}
        maxLength={3000}
        value={text}
        error={error}
        hint={needsInfo ? 'После ответа заявка автоматически вернётся в работу деканата.' : undefined}
        onChange={(e) => setText(e.target.value)}
      />
      <div>
        <Button type="submit" variant="primary" icon={<Send size={16} />} loading={busy}>
          Отправить
        </Button>
      </div>
    </form>
  );
}

function DraftEditor({ app }: { app: ApplicationDetail }) {
  const typesQ = useApplicationTypes();
  const update = useUpdateDraft(app.id);
  const action = useApplicationAction(app.id);
  const toast = useToast();
  const [busy, setBusy] = useState<'submit' | 'draft' | null>(null);
  const [errs, setErrs] = useState<FieldErrors>({});
  const [msg, setMsg] = useState<string | null>(null);
  const type = typesQ.data?.items.find((t) => t.key === app.type_key);
  if (!type) return null;

  const fail = (err: unknown) => {
    if (err instanceof ApiError && err.errors.length) setErrs(err.fieldErrors);
    setMsg(err instanceof ApiError ? err.message : 'Не удалось сохранить. Попробуйте ещё раз.');
  };
  const save = (payload: Payload, submit: boolean) => {
    setBusy(submit ? 'submit' : 'draft');
    setErrs({});
    setMsg(null);
    update.mutate(payload, {
      onSuccess: () => {
        if (!submit) {
          toast.success('Черновик сохранён');
          setBusy(null);
          return;
        }
        action.mutate('submit', {
          onSuccess: (a) => toast.success(`Заявка № ${a.number} отправлена`),
          onError: fail,
          onSettled: () => setBusy(null),
        });
      },
      onError: (e) => {
        fail(e);
        setBusy(null);
      },
    });
  };
  return (
    <Card aria-labelledby="draft-title">
      <CardHeader id="draft-title" title="Данные заявки" level={2} />
      {msg && (
        <Callout tone="critical" role="alert">
          {msg}
        </Callout>
      )}
      <ApplicationForm type={type} initial={app.payload} busy={busy} serverErrors={errs} onSubmit={save} />
    </Card>
  );
}

export default function ApplicationPage() {
  const { id: rawId } = useParams();
  const id = Number(rawId);
  const navigate = useNavigate();
  const toast = useToast();
  const q = useApplication(id);
  const action = useApplicationAction(id);
  const del = useDeleteDraft(id);
  const send = useSendMessage(id);
  const [confirm, setConfirm] = useState<'withdraw' | 'delete' | null>(null);

  if (q.isPending) return <PageSkeleton cards={3} />;
  if (q.isError)
    return (
      <div className="stack">
        <PageHeader title="Заявка" back={{ to: '/applications', label: 'Заявки' }} />
        <Card>
          <ErrorState
            error={q.error}
            title={q.error instanceof ApiError && q.error.status === 404 ? 'Заявка не найдена' : undefined}
            onRetry={() => void q.refetch()}
            retrying={q.isFetching}
          />
        </Card>
      </div>
    );
  const a = q.data;
  const tone = STATUS_META[a.status]?.tone ?? 'accent';
  const perms = a.permissions;

  const doConfirm = () => {
    if (confirm === 'withdraw')
      action.mutate('withdraw', {
        onSuccess: () => toast.success('Заявка отозвана'),
        onError: (e) => toast.error(e instanceof ApiError ? e.message : 'Не удалось отозвать заявку'),
        onSettled: () => setConfirm(null),
      });
    if (confirm === 'delete')
      del.mutate(undefined, {
        onSuccess: () => {
          toast.success('Черновик удалён');
          navigate('/applications?status=draft', { replace: true });
        },
        onError: (e) => toast.error(e instanceof ApiError ? e.message : 'Не удалось удалить черновик'),
        onSettled: () => setConfirm(null),
      });
  };

  return (
    <div className="stack">
      <PageHeader
        title={a.title}
        back={{ to: '/applications', label: 'Заявки' }}
        subtitle={
          <span className="num">
            № {a.number} · создана {formatDateTime(a.created_at)}
          </span>
        }
      />
      <Card className="status-hero" aria-labelledby="st-title">
        <h2 className="sr-only" id="st-title">
          Статус
        </h2>
        <div className="row-wrap">
          <StatusPill status={a.status} label={a.status_label} size="md" />
          <span className="xsmall muted num">обновлено {formatDateTime(a.updated_at)}</span>
        </div>
        <p className={`next-step tone-${tone}`}>
          <ArrowRightCircle aria-hidden="true" />
          <span>
            <strong>Что дальше: </strong>
            {a.next_step}
          </span>
        </p>
        <div className="row-wrap">
          {a.document_available && (
            <ButtonLink to={`/applications/${a.id}/document`} variant="primary" icon={<FileText size={18} />}>
              Открыть электронный документ
            </ButtonLink>
          )}
          {perms.can_withdraw && (
            <Button variant="secondary" icon={<Undo2 size={16} />} onClick={() => setConfirm('withdraw')}>
              Отозвать заявку
            </Button>
          )}
          {perms.can_delete && (
            <Button variant="danger" icon={<Trash2 size={16} />} onClick={() => setConfirm('delete')}>
              Удалить черновик
            </Button>
          )}
        </div>
      </Card>

      {a.status === 'needs_info' && (
        <Callout tone="medium" icon={<MessageSquareReply size={18} />} title="Деканат ждёт вашего ответа">
          Прочитайте комментарий в переписке и ответьте — заявка вернётся в работу.
        </Callout>
      )}

      {perms.can_edit ? (
        <DraftEditor app={a} />
      ) : (
        <div className="grid-2">
          <div className="col stack">
            <Card aria-labelledby="data-title">
              <CardHeader id="data-title" title="Данные заявки" level={2} />
              <dl className="dl small">
                {a.payload_display.map((p) => (
                  <div key={p.name} className="dl__row">
                    <dt>{p.label}</dt>
                    <dd style={{ whiteSpace: 'pre-wrap' }}>{p.value}</dd>
                  </div>
                ))}
              </dl>
            </Card>
            <Card aria-labelledby="chat-title">
              <CardHeader id="chat-title" title="Переписка с деканатом" level={2} />
              <Chat messages={a.messages} emptyText="Сообщений пока нет. Если появится вопрос по заявке — напишите здесь." />
              {perms.can_reply && (
                <div style={{ marginTop: 16 }}>
                  <ReplyForm
                    busy={send.isPending}
                    needsInfo={a.status === 'needs_info'}
                    onSend={(text, done) =>
                      send.mutate(text, {
                        onSuccess: (r) => {
                          done();
                          toast.success(
                            r.status === 'submitted' && a.status === 'needs_info' ? 'Ответ отправлен, заявка снова в работе' : 'Сообщение отправлено',
                          );
                        },
                        onError: (e) => toast.error(e instanceof ApiError ? e.message : 'Не удалось отправить сообщение'),
                      })
                    }
                  />
                </div>
              )}
            </Card>
          </div>
          <div className="col">
            <Card aria-labelledby="hist-title">
              <CardHeader id="hist-title" title="История статусов" level={2} />
              <Timeline items={a.history} />
            </Card>
          </div>
        </div>
      )}

      <Modal
        open={confirm !== null}
        onClose={() => setConfirm(null)}
        title={confirm === 'delete' ? 'Удалить черновик?' : 'Отозвать заявку?'}
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirm(null)}>
              Отмена
            </Button>
            <Button variant="danger-solid" loading={action.isPending || del.isPending} onClick={doConfirm}>
              {confirm === 'delete' ? 'Удалить' : 'Отозвать'}
            </Button>
          </>
        }
      >
        <p>
          {confirm === 'delete'
            ? 'Черновик будет удалён без возможности восстановления.'
            : 'Деканат не будет обрабатывать эту заявку. При необходимости её можно будет подать заново.'}
        </p>
      </Modal>
    </div>
  );
}
