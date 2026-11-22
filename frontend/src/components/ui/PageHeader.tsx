import { useEffect, type ReactNode } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ChevronLeft } from 'lucide-react';

interface PageHeaderProps {
  title: ReactNode;
  /** Текст для заголовка вкладки браузера, если title — не строка */
  docTitle?: string;
  subtitle?: ReactNode;
  back?: { to: string; label: string };
  actions?: ReactNode;
  children?: ReactNode;
}

export function useDocumentTitle(title: string | undefined) {
  useEffect(() => {
    if (title) document.title = `${title} · Цифровой деканат`;
  }, [title]);
}

/** Есть ли куда вернуться внутри приложения (react-router хранит порядковый номер записи истории). */
function canGoBack(): boolean {
  const st = window.history.state as { idx?: number } | null;
  return (st?.idx ?? 0) > 0;
}

export function PageHeader({ title, docTitle, subtitle, back, actions, children }: PageHeaderProps) {
  useDocumentTitle(docTitle ?? (typeof title === 'string' ? title : undefined));
  const navigate = useNavigate();
  const historyBack = back ? canGoBack() : false;
  return (
    <header className="page-header">
      {back && (
        <Link
          className="page-header__back"
          to={back.to}
          onClick={(e) => {
            // «Назад» возвращает туда, откуда пришёл пользователь (уведомления, расписание, главная…);
            // при прямом заходе по ссылке — в родительский раздел.
            if (historyBack) {
              e.preventDefault();
              navigate(-1);
            }
          }}
        >
          <ChevronLeft aria-hidden="true" />
          <span>{historyBack ? 'Назад' : back.label}</span>
        </Link>
      )}
      <div className="page-header__row">
        <div className="page-header__titles">
          <h1 className="page-title" id="page-title" tabIndex={-1}>
            {title}
          </h1>
          {subtitle && <div className="page-subtitle">{subtitle}</div>}
        </div>
        {actions && <div className="page-header__actions">{actions}</div>}
      </div>
      {children}
    </header>
  );
}
