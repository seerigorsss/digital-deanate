import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import type { ApplicationBrief, ApplicationListItem, ApplicationStatus } from '../../api/types';
import { formatDateTime, formatRelativeDay } from '../../lib/format';
import { STATUS_META } from '../../lib/semantics';
import { StatusPill } from '../ui/Badge';

const HINTS: Partial<Record<ApplicationStatus, string>> = {
  draft: 'Не отправлена — допишите и отправьте',
  submitted: 'Ждёт обработки',
  in_progress: 'В работе у деканата',
  needs_info: 'Нужен ваш ответ',
  approved: 'Решение принято',
  ready: 'Можно получить',
};

export function applicationHint(status: ApplicationStatus): string | undefined {
  return HINTS[status];
}

interface Props {
  app: ApplicationListItem | ApplicationBrief;
  today?: string;
}

export function ApplicationRow({ app, today }: Props) {
  const meta = STATUS_META[app.status];
  const Icon = meta.icon;
  const created = 'created_at' in app ? app.created_at : app.updated_at;
  const summary = 'summary' in app ? app.summary : '';
  const hint = applicationHint(app.status);
  return (
    <Link to={`/applications/${app.id}`} className={`list-row app-row ${app.status === 'needs_info' ? 'app-row--attention' : ''}`}>
      <span className={`list-row__icon tone-${meta.tone === 'success-strong' ? 'success' : meta.tone}`} aria-hidden="true">
        <Icon />
      </span>
      <span className="list-row__body">
        <span className="list-row__title">{app.title}</span>
        <span className="list-row__meta num">
          № {app.number} · {'created_at' in app ? `от ${formatRelativeDay(created, today)}` : `обновлена ${formatDateTime(app.updated_at)}`}
        </span>
        {summary && <span className="list-row__meta app-row__summary">{summary}</span>}
        <span className="row-wrap" style={{ marginTop: 6 }}>
          <StatusPill status={app.status} label={app.status_label} />
          {hint && app.status !== 'draft' && <span className="xsmall text-2 strong">{hint}</span>}
        </span>
      </span>
      <ChevronRight className="list-row__chevron" aria-hidden="true" />
    </Link>
  );
}
