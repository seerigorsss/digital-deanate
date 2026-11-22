import { HelpCircle, LogOut } from 'lucide-react';
import { useMeta, useProfile } from '../api/hooks';
import { useAuth } from '../auth/AuthContext';
import { Avatar } from '../components/ui/Avatar';
import { Button, ButtonLink } from '../components/ui/Button';
import { Callout } from '../components/ui/Callout';
import { Card, CardHeader } from '../components/ui/Card';
import { PageHeader } from '../components/ui/PageHeader';
import { ErrorState, PageSkeleton } from '../components/ui/States';

export default function ProfilePage() {
  const q = useProfile();
  const meta = useMeta();
  const { user, logout } = useAuth();

  if (q.isPending) return <PageSkeleton cards={2} />;
  if (q.isError)
    return (
      <Card>
        <ErrorState error={q.error} onRetry={() => void q.refetch()} retrying={q.isFetching} />
      </Card>
    );
  const p = q.data;
  const rows: [string, string | number | null][] = [
    ['Университет', p.university],
    ['Факультет', `${p.faculty.name} (${p.faculty.code})`],
    ['Направление подготовки', `${p.program.code} ${p.program.name}`],
    ['Профиль', p.program.profile],
    ['Уровень образования', p.education_level],
    ['Форма обучения', p.study_form],
    ['Основа обучения', p.funding],
    ['Курс', p.course],
    ['Группа', p.group],
    ['Номер зачётной книжки', p.record_book_number],
    ['Год поступления', p.enrollment_year],
    ['Куратор группы', p.curator],
    ['E-mail', p.email],
    ['Логин', p.login],
  ];
  return (
    <div className="stack">
      <PageHeader title="Профиль" />
      <Card className="profile-hero">
        <Avatar initials={user?.initials ?? ''} size="lg" />
        <div className="stack-xs">
          <h2 className="card-title">{p.full_name}</h2>
          <p className="small muted">
            {p.group} · {p.course} курс · {p.faculty.code}
          </p>
        </div>
      </Card>
      <Card aria-labelledby="pd-title">
        <CardHeader id="pd-title" title="Учебные данные" level={2} />
        <dl className="dl">
          {rows
            .filter(([, v]) => v != null && v !== '')
            .map(([k, v]) => (
              <div key={k} className="dl__row">
                <dt>{k}</dt>
                <dd className={typeof v === 'number' ? 'num' : undefined}>{v}</dd>
              </div>
            ))}
        </dl>
        <p className="xsmall muted" style={{ marginTop: 12 }}>
          Если данные указаны неверно, напишите в деканат через «Обращение в деканат».
        </p>
      </Card>
      {meta.data && <Callout tone="nodata">{meta.data.disclaimer}</Callout>}
      <div className="row-wrap">
        <ButtonLink to="/help" icon={<HelpCircle size={18} />}>
          Помощь и FAQ
        </ButtonLink>
        <Button
          variant="danger"
          icon={<LogOut size={18} />}
          onClick={() => void logout()}
        >
          Выйти
        </Button>
      </div>
    </div>
  );
}
