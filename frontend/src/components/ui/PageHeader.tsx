import { useEffect, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
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

export function PageHeader({ title, docTitle, subtitle, back, actions, children }: PageHeaderProps) {
  useDocumentTitle(docTitle ?? (typeof title === 'string' ? title : undefined));
  return (
    <header className="page-header">
      {back && (
        <Link className="page-header__back" to={back.to}>
          <ChevronLeft aria-hidden="true" />
          <span>{back.label}</span>
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
