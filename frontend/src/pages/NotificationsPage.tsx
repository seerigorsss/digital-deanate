import { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { BellOff, CheckCheck } from 'lucide-react';
import { useMarkAllRead, useMarkRead, useNotifications } from '../api/hooks';
import type { NotificationCategory, NotificationItem } from '../api/types';
import { NotificationRow } from '../components/domain/NotificationRow';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { NotificationDetail } from '../components/domain/NotificationDetail';
import { PageHeader } from '../components/ui/PageHeader';
import { Segmented } from '../components/ui/Segmented';
import { EmptyState, ErrorState, SkeletonCard } from '../components/ui/States';
import { useToast } from '../components/ui/Toast';
import { dateTimeToISODay, formatRelativeDay } from '../lib/format';
import { NOTIFICATION_CATEGORIES, NOTIFICATION_META } from '../lib/semantics';

type Cat = NotificationCategory | 'all';

export default function NotificationsPage() {
  const [params, setParams] = useSearchParams();
  const toast = useToast();
  const rawCat = params.get('category') as Cat | null;
  const category: Cat = rawCat && (rawCat === 'all' || NOTIFICATION_CATEGORIES.includes(rawCat as NotificationCategory)) ? rawCat : 'all';
  const unreadOnly = params.get('unread') === '1';
  const q = useNotifications(category, unreadOnly);
  const markRead = useMarkRead();
  const markAll = useMarkAllRead();

  const update = (next: { category?: Cat; unread?: boolean }) => {
    const p = new URLSearchParams(params);
    const c = next.category ?? category;
    const u = next.unread ?? unreadOnly;
    if (c === 'all') p.delete('category');
    else p.set('category', c);
    if (u) p.set('unread', '1');
    else p.delete('unread');
    setParams(p, { replace: true });
  };

  const [selected, setSelected] = useState<NotificationItem | null>(null);
  // Сначала показываем уведомление целиком; переход к связанному разделу — по кнопке «Подробнее».
  const open = (n: NotificationItem) => {
    if (!n.is_read) markRead.mutate(n.id);
    setSelected(n);
  };

  const groups = useMemo(() => {
    const items = q.data?.items ?? [];
    const out: { day: string; items: NotificationItem[] }[] = [];
    for (const n of items) {
      const day = dateTimeToISODay(n.created_at);
      const last = out[out.length - 1];
      if (last && last.day === day) last.items.push(n);
      else out.push({ day, items: [n] });
    }
    return out;
  }, [q.data]);

  const unreadBy = q.data?.unread_by_category ?? {};
  const totalUnread = q.data?.unread_count ?? 0;
  const options = [
    { value: 'all' as Cat, label: 'Все', count: totalUnread || undefined },
    ...NOTIFICATION_CATEGORIES.map((c) => ({ value: c as Cat, label: NOTIFICATION_META[c].label, count: unreadBy[c] || undefined })),
  ];
  const catUnread = category === 'all' ? totalUnread : (unreadBy[category] ?? 0);

  return (
    <div className="stack">
      <PageHeader title="Уведомления" subtitle={totalUnread ? `Непрочитанных: ${totalUnread}` : 'Все уведомления прочитаны'}>
        <Segmented options={options} value={category} onChange={(c) => update({ category: c })} label="Категория уведомлений" />
      </PageHeader>
      <div className="notif-toolbar">
        <label className="row" style={{ gap: 8, minHeight: 44 }}>
          <input type="checkbox" checked={unreadOnly} onChange={(e) => update({ unread: e.target.checked })} />
          <span className="small">Только непрочитанные</span>
        </label>
        <Button
          variant="ghost"
          icon={<CheckCheck size={18} />}
          disabled={catUnread === 0}
          loading={markAll.isPending}
          onClick={() =>
            markAll.mutate(category, {
              onSuccess: (r) => toast.success(r.updated ? `Отмечено прочитанными: ${r.updated}` : 'Непрочитанных нет'),
              onError: () => toast.error('Не удалось отметить уведомления'),
            })
          }
        >
          Прочитать все
        </Button>
      </div>
      <Card flush>
        {q.isPending ? (
          <div className="stack-sm" style={{ padding: 16 }}>
            <SkeletonCard lines={2} />
            <SkeletonCard lines={2} />
            <SkeletonCard lines={2} />
          </div>
        ) : q.isError ? (
          <ErrorState error={q.error} onRetry={() => void q.refetch()} retrying={q.isFetching} />
        ) : groups.length === 0 ? (
          <EmptyState
            icon={<BellOff />}
            title={unreadOnly ? 'Непрочитанных уведомлений нет' : 'Уведомлений нет'}
            text={unreadOnly ? 'Снимите фильтр, чтобы увидеть все уведомления.' : 'Здесь появятся объявления деканата, сроки, изменения расписания и статусы заявок.'}
            actions={
              unreadOnly ? (
                <Button onClick={() => update({ unread: false })}>Показать все</Button>
              ) : undefined
            }
          />
        ) : (
          <div style={{ padding: '4px 16px 16px' }}>
            {groups.map((g) => (
              <section key={g.day} className="notif-group" aria-label={formatRelativeDay(g.day, undefined)}>
                <h2 className="notif-group__title">{formatRelativeDay(g.day, undefined)}</h2>
                <ul className="notif-list">
                  {g.items.map((n) => (
                    <li key={n.id}>
                      <NotificationRow n={n} onOpen={open} busy={markRead.isPending && markRead.variables === n.id} />
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
        )}
      </Card>

      <NotificationDetail n={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
