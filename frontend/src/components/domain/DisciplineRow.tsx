import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import type { DisciplineAnalytics } from '../../api/types';
import { fmtNum } from '../../lib/format';
import { RISK_META } from '../../lib/semantics';
import { RiskBadge } from '../ui/Badge';
import { PointsBar } from '../ui/PointsBar';

/** Строка дисциплины: полоса слева цвета риска, чип риска, баллы и мини-полоса с остатком. */
export function DisciplineRow({ d }: { d: DisciplineAnalytics }) {
  const tone = RISK_META[d.risk.level]?.tone ?? 'nodata';
  const nodata = d.risk.level === 'insufficient_data' && d.graded_points_max === 0;
  return (
    <Link to={`/study/${d.discipline_id}`} className={`disc-row tone-${tone}`}>
      <span className="disc-row__body">
        <span className="row-wrap">
          <RiskBadge level={d.risk.level} label={d.risk.label} />
          <span className="xsmall muted">{d.assessment_type_label}</span>
        </span>
        <span className="disc-row__title">{d.title}</span>
        <span className="disc-row__points num">
          {nodata ? (
            'баллы не внесены'
          ) : (
            <>
              <strong>{fmtNum(d.current_semester_points)}</strong> из {fmtNum(d.semester_points_max)}
              {d.remaining_points_max > 0 && <span className="muted"> · ещё можно набрать {fmtNum(d.remaining_points_max)}</span>}
            </>
          )}
        </span>
        <PointsBar
          size="sm"
          max={d.semester_points_max}
          earned={d.current_semester_points}
          remaining={d.remaining_points_max}
          missing={d.missing_points_max}
          tone={tone}
          marks={[{ value: d.semester_target, label: fmtNum(d.semester_target) }]}
        />
      </span>
      <ChevronRight className="list-row__chevron" aria-hidden="true" />
    </Link>
  );
}
