import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Save, Trash2, Users } from 'lucide-react';
import { useStaffSetResult, useStaffStudentGrades, useStaffStudents } from '../../api/hooks';
import { ApiError } from '../../api/client';
import type { StaffGradeDiscipline, StaffGradeItem } from '../../api/types';
import { RiskBadge } from '../../components/ui/Badge';
import { IconButton } from '../../components/ui/Button';
import { Callout } from '../../components/ui/Callout';
import { Card, CardHeader } from '../../components/ui/Card';
import { SelectField } from '../../components/ui/Field';
import { PageHeader } from '../../components/ui/PageHeader';
import { EmptyState, ErrorState, PageSkeleton } from '../../components/ui/States';
import { useToast } from '../../components/ui/Toast';
import { fmtNum, formatDay } from '../../lib/format';
import { MODULE_STATUS_LABEL } from '../../lib/semantics';

function ItemEditor({ item, studentId }: { item: StaffGradeItem; studentId: number }) {
  const set = useStaffSetResult(studentId);
  const toast = useToast();
  const [value, setValue] = useState(item.points == null ? '' : String(item.points));
  const [error, setError] = useState<string | null>(null);
  useEffect(() => setValue(item.points == null ? '' : String(item.points)), [item.points]);
  const dirty = value.trim() !== (item.points == null ? '' : String(item.points));

  const save = (points: number | null) => {
    setError(null);
    set.mutate(
      { item_id: item.id, points },
      {
        onSuccess: () => toast.success(points == null ? 'Балл удалён' : 'Балл сохранён', 'Аналитика студента пересчитана'),
        onError: (e) => setError(e instanceof ApiError ? e.message : 'Не удалось сохранить'),
      },
    );
  };
  const submit = () => {
    const raw = value.trim().replace(',', '.');
    if (!raw) return save(null);
    const v = Number(raw);
    if (!Number.isFinite(v) || v < 0 || v > item.max_points) {
      setError(`Допустимо от 0 до ${fmtNum(item.max_points)}`);
      return;
    }
    save(v);
  };
  return (
    <li className="staff-item-row">
      <span className="stack-xs">
        <span className="small strong">{item.title}</span>
        <span className="xsmall muted">
          максимум {fmtNum(item.max_points)}
          {item.due_date ? ` · срок ${formatDay(item.due_date)}` : ''}
          {item.points == null ? ' · балла нет' : ''}
        </span>
        {error && (
          <span className="field__error xsmall" role="alert">
            {error}
          </span>
        )}
      </span>
      <form
        className="staff-item-row__controls"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <input
          className="input"
          inputMode="decimal"
          aria-label={`Балл: ${item.title}`}
          aria-invalid={!!error}
          value={value}
          placeholder="—"
          onChange={(e) => setValue(e.target.value)}
        />
        <span className="xsmall muted num">/{fmtNum(item.max_points)}</span>
        <IconButton type="submit" label="Сохранить балл" bordered disabled={!dirty || set.isPending}>
          <Save size={18} />
        </IconButton>
        {item.points != null && (
          <IconButton type="button" label="Удалить балл" bordered disabled={set.isPending} onClick={() => save(null)}>
            <Trash2 size={18} />
          </IconButton>
        )}
      </form>
    </li>
  );
}

function DisciplineCard({ d, studentId }: { d: StaffGradeDiscipline; studentId: number }) {
  return (
    <Card aria-labelledby={`d-${d.discipline_id}`}>
      <CardHeader
        id={`d-${d.discipline_id}`}
        title={d.title}
        level={2}
        aside={<RiskBadge level={d.risk.level} label={d.risk.label} />}
      />
      <p className="recalc">
        <span className="muted">{d.assessment_label}</span>
        <span>
          Набрано <strong className="num">{fmtNum(d.current_points)}</strong> из {fmtNum(d.semester_points_max)}
        </span>
      </p>
      {d.modules.map((m) => (
        <details key={m.id} className="accordion" open={m.status !== 'completed'}>
          <summary>
            <span className="module-head">
              <span className="module-head__title">
                Модуль {m.ordinal}. {m.title}
              </span>
              <span className="module-head__meta xsmall muted">{MODULE_STATUS_LABEL[m.status]}</span>
            </span>
          </summary>
          <div className="accordion__body">
            <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
              {m.items.map((it) => (
                <ItemEditor key={it.id} item={it} studentId={studentId} />
              ))}
            </ul>
          </div>
        </details>
      ))}
    </Card>
  );
}

export default function StaffGradesPage() {
  const [params, setParams] = useSearchParams();
  const students = useStaffStudents();
  const sid = params.get('student') ? Number(params.get('student')) : null;
  const grades = useStaffStudentGrades(sid);

  if (students.isPending) return <PageSkeleton cards={2} />;
  if (students.isError)
    return (
      <Card>
        <ErrorState error={students.error} onRetry={() => void students.refetch()} />
      </Card>
    );
  return (
    <div className="stack">
      <PageHeader title="Студенты и баллы" subtitle="Выставление баллов за работы — аналитика студента пересчитывается сразу" />
      <Card>
        <SelectField label="Студент" value={sid ?? ''} onChange={(e) => setParams(e.target.value ? { student: e.target.value } : {})}>
          <option value="">Выберите студента…</option>
          {students.data.items.map((s) => (
            <option key={s.user_id} value={s.user_id}>
              {s.full_name} — {s.group}, {s.course} курс
            </option>
          ))}
        </SelectField>
      </Card>
      {sid == null ? (
        <Card>
          <EmptyState icon={<Users />} title="Выберите студента" text="Откроются его дисциплины, модули и работы с текущими баллами." />
        </Card>
      ) : grades.isPending ? (
        <PageSkeleton cards={2} />
      ) : grades.isError ? (
        <Card>
          <ErrorState error={grades.error} onRetry={() => void grades.refetch()} />
        </Card>
      ) : (
        <>
          <Callout tone="accent">
            Изменения сохраняются сразу и видны студенту: обновятся баллы, уровень риска, индекс и рекомендации, студент получит уведомление.
          </Callout>
          {grades.data.disciplines.map((d) => (
            <DisciplineCard key={d.discipline_id} d={d} studentId={sid} />
          ))}
        </>
      )}
    </div>
  );
}
