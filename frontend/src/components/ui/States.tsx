import type { CSSProperties, ReactNode } from 'react';
import { CloudOff, RefreshCw, SearchX, ServerCrash } from 'lucide-react';
import { ApiError, errorMessage } from '../../api/client';
import { Button } from './Button';

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  text?: ReactNode;
  actions?: ReactNode;
  compact?: boolean;
  tone?: string;
}

export function EmptyState({ icon, title, text, actions, compact, tone }: EmptyStateProps) {
  return (
    <div className={`state ${compact ? 'state--compact' : ''} ${tone ? `tone-${tone}` : ''}`}>
      {icon && (
        <div className="state__icon" aria-hidden="true">
          {icon}
        </div>
      )}
      <p className="state__title">{title}</p>
      {text && <div className="state__text">{text}</div>}
      {actions && <div className="state__actions">{actions}</div>}
    </div>
  );
}

interface ErrorStateProps {
  error: unknown;
  onRetry?: () => void;
  retrying?: boolean;
  compact?: boolean;
  title?: string;
}

/** Ошибка сети или сервера с понятным текстом и кнопкой «Повторить». */
export function ErrorState({ error, onRetry, retrying, compact, title }: ErrorStateProps) {
  const isNetwork = error instanceof ApiError && error.isNetwork;
  const heading = title ?? (isNetwork ? 'Нет соединения' : 'Не удалось загрузить данные');
  return (
    <div className={`state ${compact ? 'state--compact' : ''} tone-danger`} role="alert">
      <div className="state__icon" aria-hidden="true">
        {isNetwork ? <CloudOff /> : <ServerCrash />}
      </div>
      <p className="state__title">{heading}</p>
      <div className="state__text">{errorMessage(error)}</div>
      {onRetry && (
        <div className="state__actions">
          <Button variant="secondary" icon={<RefreshCw aria-hidden="true" />} onClick={onRetry} loading={retrying}>
            Повторить
          </Button>
        </div>
      )}
    </div>
  );
}

export function NoResults({ text, onReset }: { text?: string; onReset?: () => void }) {
  return (
    <EmptyState
      compact
      icon={<SearchX />}
      title="Ничего не найдено"
      text={text ?? 'Попробуйте изменить запрос или сбросить фильтр.'}
      actions={onReset && <Button onClick={onReset}>Сбросить</Button>}
    />
  );
}

export function Skeleton({ width, height = 16, radius, style, className }: { width?: number | string; height?: number | string; radius?: number; style?: CSSProperties; className?: string }) {
  return <span className={`skeleton ${className ?? ''}`} style={{ width: width ?? '100%', height, borderRadius: radius, ...style }} aria-hidden="true" />;
}

/** Скелетон карточки: заголовок и несколько строк. */
export function SkeletonCard({ lines = 3, height }: { lines?: number; height?: number }) {
  return (
    <div className="card" aria-hidden="true">
      <Skeleton width="45%" height={20} />
      <div className="stack-sm" style={{ marginTop: 16 }}>
        {height ? (
          <Skeleton height={height} radius={12} />
        ) : (
          Array.from({ length: lines }, (_, i) => <Skeleton key={i} width={`${90 - i * 12}%`} height={14} />)
        )}
      </div>
    </div>
  );
}

/** Загрузка страницы: скелетоны + текст для экранного диктора. */
export function PageSkeleton({ cards = 3 }: { cards?: number }) {
  return (
    <div className="stack" aria-busy="true">
      <span className="sr-only" role="status">
        Загрузка…
      </span>
      <Skeleton width="55%" height={30} radius={10} />
      {Array.from({ length: cards }, (_, i) => (
        <SkeletonCard key={i} lines={3 + (i % 2)} />
      ))}
    </div>
  );
}
