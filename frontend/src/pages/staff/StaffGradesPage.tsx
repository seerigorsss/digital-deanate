import { useSearchParams, Link } from 'react-router-dom';
import { ChevronRight, Users, UserRound } from 'lucide-react';
import { useStaffStructure, useStaffStudentGrades, useStaffStudents } from '../../api/hooks';
import type { OrgFaculty, StaffGradeDiscipline } from '../../api/types';
import { RiskBadge } from '../../components/ui/Badge';
import { Card, CardHeader } from '../../components/ui/Card';
import { SelectField } from '../../components/ui/Field';
import { PageHeader } from '../../components/ui/PageHeader';
import { EmptyState, ErrorState, PageSkeleton } from '../../components/ui/States';
import { fmtNum, plural } from '../../lib/format';
import { MODULE_STATUS_LABEL } from '../../lib/semantics';

/** Только просмотр: баллы приходят из системы преподавателя, деканат их не меняет. */
function DisciplineCard({ d }: { d: StaffGradeDiscipline }) {
  return (
    <Card aria-labelledby={`d-${d.discipline_id}`}>
      <CardHeader id={`d-${d.discipline_id}`} title={d.title} level={2} />
      <p className="recalc">
        <RiskBadge level={d.risk.level} label={d.risk.label} />
        <span className="muted">{d.assessment_label}</span>
        <span>
          Набрано <strong className="num">{fmtNum(d.current_points)}</strong> из {fmtNum(d.semester_points_max)}
        </span>
      </p>
      {d.modules.map((m) => (
        <details key={m.id} className="accordion">
          <summary>
            <span className="module-head">
              <span className="module-head__title">
                Модуль {m.ordinal}. {m.title}
              </span>
              <span className="module-head__meta xsmall muted">{MODULE_STATUS_LABEL[m.status]}</span>
            </span>
          </summary>
          <div className="accordion__body">
            <ul className="staff-items">
              {m.items.map((it) => (
                <li key={it.id} className="staff-item-row">
                  <span className="small">{it.title}</span>
                  <span className="small num strong">
                    {it.points == null ? <span className="muted">—</span> : fmtNum(it.points)}
                    <span className="muted"> / {fmtNum(it.max_points)}</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </details>
      ))}
    </Card>
  );
}

function StudentView({ sid }: { sid: number }) {
  const grades = useStaffStudentGrades(sid);
  if (grades.isPending) return <PageSkeleton cards={2} />;
  if (grades.isError)
    return (
      <Card>
        <ErrorState error={grades.error} onRetry={() => void grades.refetch()} />
      </Card>
    );
  const s = grades.data.student;
  return (
    <>
      <Card>
        <p className="strong">{s.full_name}</p>
        <p className="small muted">
          {s.group}, {s.course} курс · {s.email}
        </p>
      </Card>
      {grades.data.disciplines.length === 0 ? (
        <Card>
          <EmptyState compact title="Дисциплин в семестре нет" />
        </Card>
      ) : (
        grades.data.disciplines.map((d) => <DisciplineCard key={d.discipline_id} d={d} />)
      )}
    </>
  );
}

function GroupStudents({ group, base }: { group: string; base: URLSearchParams }) {
  const students = useStaffStudents(group);
  if (students.isPending) return <PageSkeleton cards={1} />;
  if (students.isError)
    return (
      <Card>
        <ErrorState error={students.error} onRetry={() => void students.refetch()} />
      </Card>
    );
  const items = students.data.items;
  return (
    <Card aria-labelledby="group-title">
      <CardHeader id="group-title" title={`Группа ${group}`} level={2} />
      {items.length === 0 ? (
        <EmptyState
          compact
          icon={<Users />}
          title="В группе пока нет студентов"
          text="Состав появится после зачисления или перевода студентов в эту группу."
        />
      ) : (
        <ul className="list">
          {items.map((st) => {
            const q = new URLSearchParams(base);
            q.set('student', String(st.user_id));
            return (
              <li key={st.user_id}>
                <Link to={`?${q.toString()}`} className="list-row">
                  <span className="list-row__icon" aria-hidden="true">
                    <UserRound />
                  </span>
                  <span className="list-row__body">
                    <span className="list-row__title">{st.full_name}</span>
                    <span className="list-row__meta">
                      {st.course} курс · {st.email}
                    </span>
                  </span>
                  <ChevronRight className="list-row__chevron" aria-hidden="true" size={18} />
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}

export default function StaffGradesPage() {
  const [params, setParams] = useSearchParams();
  const structure = useStaffStructure();
  const fac = params.get('faculty') ?? '';
  const dep = params.get('department') ?? '';
  const grp = params.get('group') ?? '';
  const sidRaw = params.get('student');
  const sid = sidRaw && /^\d+$/.test(sidRaw) ? Number(sidRaw) : null;

  if (structure.isPending) return <PageSkeleton cards={2} />;
  if (structure.isError)
    return (
      <Card>
        <ErrorState error={structure.error} onRetry={() => void structure.refetch()} />
      </Card>
    );

  const faculties: OrgFaculty[] = structure.data.faculties;
  const faculty = faculties.find((f) => f.code === fac);
  const department = faculty?.departments.find((d) => d.code === dep);
  const group = department?.groups.find((g) => g.name === grp);

  // Каждый уровень выбора — отдельная запись истории, чтобы «Назад» в браузере возвращал на шаг выше.
  const choose = (next: Record<string, string>) => {
    const q: Record<string, string> = {};
    for (const [k, v] of Object.entries(next)) if (v) q[k] = v;
    setParams(q);
  };
  const base = new URLSearchParams({ faculty: fac, department: dep, group: grp });

  return (
    <div className="stack">
      <PageHeader
        title="Успеваемость студентов"
        subtitle="Выберите факультет, кафедру и группу. Баллы приходят из системы преподавателей — здесь только просмотр."
      />
      <Card>
        <div className="org-picker">
          <SelectField label="Факультет" value={faculty ? fac : ''} onChange={(e) => choose({ faculty: e.target.value })}>
            <option value="">Выберите факультет…</option>
            {faculties.map((f) => (
              <option key={f.code} value={f.code}>
                {f.code} — {f.name}
              </option>
            ))}
          </SelectField>
          <SelectField
            label="Кафедра"
            value={department ? dep : ''}
            disabled={!faculty}
            onChange={(e) => choose({ faculty: fac, department: e.target.value })}
          >
            <option value="">{faculty ? 'Выберите кафедру…' : 'Сначала факультет'}</option>
            {faculty?.departments.map((d) => (
              <option key={d.code} value={d.code}>
                {d.code} — {d.name}
              </option>
            ))}
          </SelectField>
          <SelectField
            label="Группа"
            value={group ? grp : ''}
            disabled={!department || department.groups.length === 0}
            onChange={(e) => choose({ faculty: fac, department: dep, group: e.target.value })}
          >
            <option value="">
              {!department ? 'Сначала кафедра' : department.groups.length === 0 ? 'Групп пока нет' : 'Выберите группу…'}
            </option>
            {department?.groups.map((g) => (
              <option key={g.name} value={g.name}>
                {g.name} · {g.course} курс · {g.students_count === 0 ? 'нет студентов' : `${g.students_count} ${plural(g.students_count, ['студент', 'студента', 'студентов'])}`}
              </option>
            ))}
          </SelectField>
        </div>
      </Card>

      {sid != null && group ? (
        <StudentView sid={sid} />
      ) : group ? (
        <GroupStudents group={group.name} base={base} />
      ) : department && department.groups.length === 0 ? (
        <Card>
          <EmptyState icon={<Users />} title="На кафедре пока нет учебных групп" text="Группы появятся после формирования набора." />
        </Card>
      ) : (
        <Card>
          <EmptyState
            icon={<Users />}
            title={!faculty ? 'Выберите факультет' : !department ? 'Выберите кафедру' : 'Выберите группу'}
            text="Откроется список студентов группы, затем — успеваемость выбранного студента по дисциплинам."
          />
        </Card>
      )}
    </div>
  );
}
