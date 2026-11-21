import { useRef, type KeyboardEvent, type ReactNode } from 'react';

export interface SegmentOption<T extends string> {
  value: T;
  label: ReactNode;
  count?: number;
  icon?: ReactNode;
}

interface SegmentedProps<T extends string> {
  options: SegmentOption<T>[];
  value: T;
  onChange: (value: T) => void;
  label: string;
  block?: boolean;
  /** tabs — роль tablist (переключение вкладок), иначе группа кнопок-переключателей */
  mode?: 'tabs' | 'toggle';
  controls?: string;
}

/** Сегментированный переключатель / вкладки с навигацией стрелками. */
export function Segmented<T extends string>({ options, value, onChange, label, block, mode = 'toggle', controls }: SegmentedProps<T>) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const isTabs = mode === 'tabs';

  const onKeyDown = (e: KeyboardEvent<HTMLButtonElement>, idx: number) => {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft' && e.key !== 'Home' && e.key !== 'End') return;
    e.preventDefault();
    let next = idx;
    if (e.key === 'ArrowRight') next = (idx + 1) % options.length;
    if (e.key === 'ArrowLeft') next = (idx - 1 + options.length) % options.length;
    if (e.key === 'Home') next = 0;
    if (e.key === 'End') next = options.length - 1;
    refs.current[next]?.focus();
    if (isTabs) onChange(options[next].value);
  };

  return (
    <div
      className={`segmented ${block ? 'segmented--block' : ''}`}
      role={isTabs ? 'tablist' : 'group'}
      aria-label={label}
    >
      {options.map((o, i) => {
        const selected = o.value === value;
        return (
          <button
            key={o.value}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            className="segmented__item"
            role={isTabs ? 'tab' : undefined}
            aria-selected={isTabs ? selected : undefined}
            aria-pressed={isTabs ? undefined : selected}
            aria-controls={isTabs ? controls : undefined}
            tabIndex={isTabs && !selected ? -1 : 0}
            onClick={() => onChange(o.value)}
            onKeyDown={(e) => onKeyDown(e, i)}
          >
            {o.icon}
            {o.label}
            {o.count !== undefined && <span className="segmented__count">{o.count}</span>}
          </button>
        );
      })}
    </div>
  );
}
