import { useParams } from 'react-router-dom';
import { Printer } from 'lucide-react';
import { useApplicationDocument } from '../api/hooks';
import { ApiError } from '../api/client';
import { Button } from '../components/ui/Button';
import { Callout } from '../components/ui/Callout';
import { Card } from '../components/ui/Card';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState, ErrorState, PageSkeleton } from '../components/ui/States';
import { formatDate } from '../lib/format';

const PAYLOAD_LABELS: Record<string, string> = {
  destination: 'Место предоставления',
  copies: 'Количество экземпляров',
  period_from: 'Период с',
  period_to: 'Период по',
  military_office: 'Военный комиссариат',
  scope: 'Период выписки',
  language: 'Язык',
};
const VALUE_LABELS: Record<string, string> = { all: 'все завершённые семестры', last: 'последний семестр', ru: 'русский', en: 'английский' };

export default function DocumentPage() {
  const { id: rawId } = useParams();
  const id = Number(rawId);
  const q = useApplicationDocument(id);
  const back = { to: `/applications/${id}`, label: 'К заявке' };

  if (q.isPending) return <PageSkeleton cards={1} />;
  if (q.isError)
    return (
      <div className="stack">
        <PageHeader title="Электронный документ" back={back} />
        <Card>
          {q.error instanceof ApiError && q.error.status === 404 ? (
            <EmptyState title="Документ недоступен" text="Электронный документ появляется, когда заявка с электронной выдачей готова." />
          ) : (
            <ErrorState error={q.error} onRetry={() => void q.refetch()} />
          )}
        </Card>
      </div>
    );
  const d = q.data;
  const rows = Object.entries(d.payload).filter(([k]) => PAYLOAD_LABELS[k]);
  return (
    <div className="stack">
      <PageHeader
        title="Электронный документ"
        back={back}
        actions={
          <Button icon={<Printer size={18} />} onClick={() => window.print()}>
            Печать / PDF
          </Button>
        }
      />
      <Callout tone="medium">Это демонстрационный образец в рамках конкурсного концепта, а не юридически значимый документ.</Callout>
      <article className="doc-sheet" aria-label={d.title}>
        <div className="doc-sheet__watermark" aria-hidden="true">
          <span>{d.watermark}</span>
        </div>
        <div className="doc-sheet__content">
          <p className="doc-sheet__univ">{d.university}</p>
          <h2 className="doc-sheet__title">{d.title}</h2>
          <p className="small num">
            № {d.number} от {formatDate(d.issued_on)}
          </p>
          <p>
            Настоящим подтверждается, что <strong>{d.student.full_name}</strong> является студентом(-кой) {d.student.course} курса
            {` ${d.student.study_form.toLowerCase()}`} формы обучения ({d.student.funding.toLowerCase()}), факультет «{d.student.faculty}»,
            направление подготовки {d.student.program}, группа {d.student.group}.
          </p>
          <table className="doc-sheet__table">
            <tbody>
              <tr>
                <th scope="row">Номер зачётной книжки</th>
                <td className="num">{d.student.record_book_number}</td>
              </tr>
              {rows.map(([k, v]) => (
                <tr key={k}>
                  <th scope="row">{PAYLOAD_LABELS[k]}</th>
                  <td>{k.startsWith('period') ? formatDate(String(v)) : (VALUE_LABELS[String(v)] ?? String(v))}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="doc-stamp">
            <span className="xsmall muted">Код проверки</span>
            <span className="num strong">{d.verification_code}</span>
          </div>
        </div>
      </article>
    </div>
  );
}
