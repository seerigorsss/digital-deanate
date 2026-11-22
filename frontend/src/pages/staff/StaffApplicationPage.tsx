import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useStaffApplication, useStaffChangeStatus, useStaffSendMessage } from '../../api/hooks';
import { ApiError } from '../../api/client';
import type { StaffTransition } from '../../api/types';
import { StatusPill } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card, CardHeader } from '../../components/ui/Card';
import { TextAreaField } from '../../components/ui/Field';
import { PageHeader } from '../../components/ui/PageHeader';
import { ErrorState, PageSkeleton } from '../../components/ui/States';
import { useToast } from '../../components/ui/Toast';
import { formatDateTime } from '../../lib/format';
import { Chat, ReplyForm, Timeline } from '../ApplicationPage';

export default function StaffApplicationPage() {
  const { id: rawId } = useParams();
  const id = Number(rawId);
  const q = useStaffApplication(id);
  const change = useStaffChangeStatus(id);
  const send = useStaffSendMessage(id);
  const toast = useToast();
  const [target, setTarget] = useState<StaffTransition | null>(null);
  const [comment, setComment] = useState('');
  const [error, setError] = useState<string | null>(null);

  if (q.isPending) return <PageSkeleton cards={3} />;
  if (q.isError)
    return (
      <div className="stack">
        <PageHeader title="Заявка" back={{ to: '/staff', label: 'Очередь' }} />
        <Card>
          <ErrorState error={q.error} onRetry={() => void q.refetch()} retrying={q.isFetching} />
        </Card>
      </div>
    );
  const a = q.data;

  const apply = () => {
    if (!target) return;
    if (target.comment_required && !comment.trim()) {
      setError('Для этого статуса нужен комментарий для студента');
      return;
    }
    setError(null);
    change.mutate(
      { to_status: target.status, comment: comment.trim() || null },
      {
        onSuccess: () => {
          toast.success(`Статус изменён: ${target.label}`, 'Студент получил уведомление');
          setTarget(null);
          setComment('');
        },
        onError: (e) => setError(e instanceof ApiError ? e.message : 'Не удалось изменить статус'),
      },
    );
  };

  return (
    <div className="stack">
      <PageHeader
        title={a.title}
        back={{ to: '/staff', label: 'Очередь' }}
        subtitle={
          <span className="num">
            № {a.number} · {a.student ? `${a.student.full_name}, ${a.student.group}, ${a.student.course} курс` : ''}
          </span>
        }
      />
      <Card className="status-hero" aria-labelledby="st">
        <h2 className="card-title" id="st">
          Статус
        </h2>
        <div className="row-wrap">
          <StatusPill status={a.status} label={a.status_label} size="md" />
          <span className="xsmall muted">подана {a.submitted_at ? formatDateTime(a.submitted_at) : '—'}</span>
        </div>
        {a.allowed_transitions.length === 0 ? (
          <p className="small muted">Заявка закрыта — дальнейшие действия недоступны.</p>
        ) : (
          <div className="stack-sm">
            <span className="small strong">Перевести в статус:</span>
            <div className="row-wrap">
              {a.allowed_transitions.map((t) => (
                <Button
                  key={t.status}
                  variant={target?.status === t.status ? 'primary' : 'secondary'}
                  aria-pressed={target?.status === t.status}
                  onClick={() => {
                    setTarget(t);
                    setError(null);
                  }}
                >
                  {t.label}
                </Button>
              ))}
            </div>
            {target && (
              <div className="stack-sm">
                <TextAreaField
                  label={target.comment_required ? 'Комментарий для студента (обязательно)' : 'Комментарий для студента'}
                  name="comment"
                  rows={3}
                  maxLength={2000}
                  value={comment}
                  error={error}
                  required={target.comment_required}
                  onChange={(e) => setComment(e.target.value)}
                />
                <div className="row-wrap">
                  <Button variant="primary" loading={change.isPending} onClick={apply}>
                    Применить: {target.label}
                  </Button>
                  <Button variant="ghost" onClick={() => setTarget(null)}>
                    Отмена
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
      </Card>
      <div className="grid-2">
        <div className="col stack">
          <Card aria-labelledby="data">
            <CardHeader id="data" title="Данные заявки" level={2} />
            <dl className="dl small">
              {a.payload_display.map((p) => (
                <div key={p.name} className="dl__row">
                  <dt>{p.label}</dt>
                  <dd style={{ whiteSpace: 'pre-wrap' }}>{p.value}</dd>
                </div>
              ))}
            </dl>
          </Card>
          <Card aria-labelledby="chat">
            <CardHeader id="chat" title="Переписка со студентом" level={2} />
            <Chat messages={a.messages} emptyText="Сообщений пока нет." />
            {a.permissions.can_reply && (
              <div style={{ marginTop: 16 }}>
                <ReplyForm
                  busy={send.isPending}
                  onSend={(text, done) =>
                    send.mutate(text, {
                      onSuccess: () => {
                        done();
                        toast.success('Ответ отправлен студенту');
                      },
                      onError: (e) => toast.error(e instanceof ApiError ? e.message : 'Не удалось отправить'),
                    })
                  }
                />
              </div>
            )}
          </Card>
        </div>
        <Card aria-labelledby="hist">
          <CardHeader id="hist" title="История" level={2} />
          <Timeline items={a.history} viewer="staff" />
        </Card>
      </div>
    </div>
  );
}
