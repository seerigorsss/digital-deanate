import { useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import type { NotificationItem } from '../../api/types';
import { Button } from '../ui/Button';
import { Modal } from '../ui/Modal';
import { formatDateTime, isInternalLink } from '../../lib/format';
import { NOTIFICATION_META } from '../../lib/semantics';

/** Окно с полным текстом уведомления; переход к связанному разделу — только по кнопке «Подробнее». */
export function NotificationDetail({ n, onClose }: { n: NotificationItem | null; onClose: () => void }) {
  const navigate = useNavigate();
  const link = n && isInternalLink(n.link) && n.link !== '/notifications' ? n.link : null;
  return (
    <Modal
      open={n !== null}
      onClose={onClose}
      title={n?.title ?? ''}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            Закрыть
          </Button>
          {link && (
            <Button
              variant="primary"
              icon={<ArrowRight size={18} />}
              onClick={() => {
                onClose();
                navigate(link);
              }}
            >
              Подробнее
            </Button>
          )}
        </>
      }
    >
      {n && (
        <div className="stack-sm">
          <span className="xsmall muted">
            {NOTIFICATION_META[n.category]?.label ?? 'Уведомление'} · {formatDateTime(n.created_at)}
          </span>
          <p style={{ whiteSpace: 'pre-wrap' }}>{n.body}</p>
        </div>
      )}
    </Modal>
  );
}
