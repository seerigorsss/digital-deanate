import { Compass } from 'lucide-react';
import { useDocumentTitle } from '../components/ui/PageHeader';
import { ButtonLink } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/States';

export function NotFoundPage({ standalone }: { standalone?: boolean }) {
  useDocumentTitle('Страница не найдена');
  const body = (
    <Card>
      <EmptyState
        icon={<Compass />}
        title="Страница не найдена"
        text="Возможно, ссылка устарела или в адресе опечатка."
        actions={
          <ButtonLink to={standalone ? '/login' : '/'} variant="primary">
            {standalone ? 'Ко входу' : 'На главную'}
          </ButtonLink>
        }
      />
    </Card>
  );
  if (!standalone) return body;
  return (
    <div className="auth-page">
      <div className="auth-wrap">{body}</div>
    </div>
  );
}
