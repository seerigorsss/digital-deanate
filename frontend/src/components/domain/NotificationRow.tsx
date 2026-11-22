import type { NotificationItem } from '../../api/types';
import { formatDateTime } from '../../lib/format';
import { NOTIFICATION_META } from '../../lib/semantics';
import { Badge } from '../ui/Badge';

interface Props {
  n: NotificationItem;
  onOpen: (n: NotificationItem) => void;
  clamp?: boolean;
  busy?: boolean;
}

/** Уведомление-строка: нажатие отмечает прочитанным и ведёт по ссылке. Непрочитанное — точка, жирный заголовок и подложка. */
export function NotificationRow({ n, onOpen, clamp, busy }: Props) {
  const meta = NOTIFICATION_META[n.category] ?? NOTIFICATION_META.announcement;
  const Icon = meta.icon;
  return (
    <button
      type="button"
      className={`notif ${n.is_read ? '' : 'notif--unread'} ${clamp ? 'notif--clamp' : ''}`}
      onClick={() => onOpen(n)}
      disabled={busy}
    >
      <span className="list-row__icon tone-accent" aria-hidden="true">
        <Icon />
      </span>
      <span className="notif__body">
        <span className="notif__top">
          {!n.is_read && <span className="dot" aria-hidden="true" />}
          <span className="notif__title">{n.title}</span>
        </span>
        <span className="notif__text">{n.body}</span>
        <span className="notif__meta">
          <span>{meta.label}</span>
          <span aria-hidden="true">·</span>
          <time dateTime={n.created_at}>{formatDateTime(n.created_at)}</time>
          {n.importance === 'high' && <Badge tone="attention">Важно</Badge>}
          {!n.is_read && <span className="sr-only">, непрочитанное</span>}
        </span>
      </span>
    </button>
  );
}
