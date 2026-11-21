import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from 'react';
import { CircleAlert, CircleCheck, Info, X } from 'lucide-react';

type ToastTone = 'success' | 'error' | 'info';

interface ToastItem {
  id: number;
  tone: ToastTone;
  title: string;
  text?: string;
}

interface ToastApi {
  show: (t: { title: string; text?: string; tone?: ToastTone }) => void;
  success: (title: string, text?: string) => void;
  error: (title: string, text?: string) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

const ICONS = { success: CircleCheck, error: CircleAlert, info: Info };

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const counter = useRef(0);

  const dismiss = useCallback((id: number) => setItems((list) => list.filter((t) => t.id !== id)), []);

  const show = useCallback<ToastApi['show']>(
    ({ title, text, tone = 'info' }) => {
      const id = ++counter.current;
      setItems((list) => [...list.slice(-2), { id, title, text, tone }]);
      window.setTimeout(() => dismiss(id), tone === 'error' ? 7000 : 4500);
    },
    [dismiss],
  );

  const api = useMemo<ToastApi>(
    () => ({
      show,
      success: (title, text) => show({ title, text, tone: 'success' }),
      error: (title, text) => show({ title, text, tone: 'error' }),
    }),
    [show],
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="toasts no-print" aria-live="polite" aria-relevant="additions">
        {items.map((t) => {
          const Icon = ICONS[t.tone];
          return (
            <div key={t.id} className={`toast toast--${t.tone}`} role={t.tone === 'error' ? 'alert' : 'status'}>
              <Icon aria-hidden="true" />
              <div className="toast__body">
                <div className="toast__title">{t.title}</div>
                {t.text && <div>{t.text}</div>}
              </div>
              <button type="button" className="icon-btn" aria-label="Закрыть уведомление" onClick={() => dismiss(t.id)}>
                <X aria-hidden="true" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used inside ToastProvider');
  return ctx;
}
