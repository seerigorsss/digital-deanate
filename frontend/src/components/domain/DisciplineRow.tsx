import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import type { DisciplineAnalytics } from '../../api/types';
import { fmtNum } from '../../lib/format';
import { RISK_META } from '../../lib/semantics';
import { RiskBadge } from '../ui/Badge';
import { ScoreBar } from './ScoreBar';

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
              <strong>{fmtNum(d.current_semester_points + (d.exam?.result ?? 0))}</strong> из 100
              {d.remaining_points_max > 0 && <span className="muted"> · в семестре можно добрать {fmtNum(d.remaining_points_max)}</span>}
            </>
          )}
        </span>
        <ScoreBar d={d} tone={tone} size="sm" />
      </span>
      <ChevronRight className="list-row__chevron" aria-hidden="true" />
    </Link>
  );
}
