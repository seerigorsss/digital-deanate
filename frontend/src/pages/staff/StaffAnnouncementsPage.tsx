import { useState, type FormEvent } from 'react';
import { Megaphone } from 'lucide-react';
import { usePublishAnnouncement, useStaffAnnouncements, useStaffGroups } from '../../api/hooks';
import { ApiError } from '../../api/client';
import { Button } from '../../components/ui/Button';
import { Card, CardHeader } from '../../components/ui/Card';
import { SelectField, TextAreaField, TextField } from '../../components/ui/Field';
import { PageHeader } from '../../components/ui/PageHeader';
import { EmptyState, ErrorState, SkeletonCard } from '../../components/ui/States';
import { useToast } from '../../components/ui/Toast';
import { formatDateTime } from '../../lib/format';

function audienceLabel(a: string): string {
  if (a === 'all') return 'Все студенты';
  if (a.startsWith('group:')) return `Группа ${a.slice(6)}`;
  if (a.startsWith('faculty:')) return `Факультет ${a.slice(8)}`;
  return a;
}

export default function StaffAnnouncementsPage() {
  const list = useStaffAnnouncements();
  const groups = useStaffGroups();
  const publish = usePublishAnnouncement();
  const toast = useToast();
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [audience, setAudience] = useState('all');
  const [important, setImportant] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const errs: Record<string, string> = {};
    if (title.trim().length < 3) errs.title = 'Минимум 3 символа';
    if (body.trim().length < 3) errs.body = 'Минимум 3 символа';
    setErrors(errs);
    if (Object.keys(errs).length) return;
    publish.mutate(
      { title: title.trim(), body: body.trim(), audience, importance: important ? 'high' : 'normal' },
      {
        onSuccess: (r) => {
          toast.success('Объявление опубликовано', `Получателей: ${r.recipients}`);
          setTitle('');
          setBody('');
          setImportant(false);
        },
        onError: (err) => {
          if (err instanceof ApiError && err.errors.length) setErrors(err.fieldErrors);
          toast.error(err instanceof ApiError ? err.message : 'Не удалось опубликовать');
        },
      },
    );
  };

  return (
    <div className="stack">
      <PageHeader title="Объявления" subtitle="Рассылка уведомлений студентам" />
      <div className="grid-2">
        <Card aria-labelledby="new-ann">
          <CardHeader id="new-ann" title="Новое объявление" level={2} icon={<Megaphone className="card-icon" aria-hidden="true" />} />
          <form className="stack" onSubmit={submit} noValidate>
            <TextField label="Заголовок" name="title" required maxLength={200} value={title} error={errors.title} onChange={(e) => setTitle(e.target.value)} />
            <TextAreaField label="Текст" name="body" required rows={5} maxLength={4000} value={body} error={errors.body} onChange={(e) => setBody(e.target.value)} />
            <SelectField label="Кому" name="audience" value={audience} onChange={(e) => setAudience(e.target.value)}>
              <option value="all">Все студенты</option>
              {(groups.data?.faculties ?? []).map(([code, name]) => (
                <option key={code} value={`faculty:${code}`}>
                  Факультет {code} — {name}
                </option>
              ))}
              {(groups.data?.groups ?? []).map((g) => (
                <option key={g} value={`group:${g}`}>
                  Группа {g}
                </option>
              ))}
            </SelectField>
            <label className="row" style={{ gap: 8, minHeight: 44 }}>
              <input type="checkbox" checked={important} onChange={(e) => setImportant(e.target.checked)} />
              <span className="small">Важное (выделяется у студента)</span>
            </label>
            <div>
              <Button type="submit" variant="primary" loading={publish.isPending}>
                Опубликовать
              </Button>
            </div>
          </form>
        </Card>
        <Card aria-labelledby="ann-list">
          <CardHeader id="ann-list" title="Опубликованные" level={2} />
          {list.isPending ? (
            <SkeletonCard lines={3} />
          ) : list.isError ? (
            <ErrorState error={list.error} onRetry={() => void list.refetch()} compact />
          ) : list.data.items.length === 0 ? (
            <EmptyState compact title="Объявлений пока нет" />
          ) : (
            <ul className="stack" style={{ listStyle: 'none', margin: 0, padding: 0 }}>
              {list.data.items.map((a) => (
                <li key={a.id} className="stack-xs">
                  <span className="strong">{a.title}</span>
                  <span className="xsmall muted">
                    {audienceLabel(a.audience)} · {formatDateTime(a.published_at)}
                  </span>
                  <p className="small">{a.body}</p>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
