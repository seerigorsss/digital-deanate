import { fmtNum } from '../../lib/format';

/** Минимум данных для шкалы: подходит и DisciplineAnalytics, и краткая запись приоритета с главной. */
export interface ScoreData {
  assessment_type: string;
  semester_points_max: number;
  current_semester_points: number;
  remaining_points_max: number;
  missing_points_max: number;
  exam?: { result: number | null; points_max?: number; points_min?: number } | null;
}

const pct = (v: number, max: number) => `${Math.max(0, Math.min(100, (v / (max || 1)) * 100))}%`;

/**
 * Единая шкала итога дисциплины.
 * Для экзамена (тип C) одна полоса 0–100 разделена на две части: семестр (до 70) и экзамен (до 30, минимум 18) —
 * сразу видно, что можно добрать в семестре, а что — только на экзамене.
 */
export function ScoreBar({ d, tone, size = 'md', legend = false }: { d: ScoreData; tone: string; size?: 'sm' | 'md'; legend?: boolean }) {
  const isExam = d.assessment_type === 'exam';
  const semMax = d.semester_points_max;
  const examMax = isExam ? (d.exam?.points_max ?? 30) : 0;
  const examMin = d.exam?.points_min ?? 18;
  const examRes = d.exam?.result ?? null;
  const total = semMax + examMax;
  const earned = d.current_semester_points;
  const aria =
    `Семестр: набрано ${fmtNum(earned)} из ${fmtNum(semMax)}` +
    (d.remaining_points_max > 0 ? `, можно добрать ещё ${fmtNum(d.remaining_points_max)}` : '') +
    (isExam ? (examRes != null ? `. Экзамен: ${fmtNum(examRes)} из ${fmtNum(examMax)}` : `. Экзамен: до ${fmtNum(examMax)} баллов, минимум ${fmtNum(examMin)}`) : '');
  return (
    <div className={`sbar ${size === 'sm' ? 'sbar--sm' : ''} tone-${tone}`}>
      <div className="sbar__track" role="img" aria-label={aria}>
        <div className="sbar__part" style={{ width: pct(semMax, total) }}>
          <span className="pbar__seg pbar__seg--earned" style={{ width: pct(earned, semMax) }} />
          {d.missing_points_max > 0 && <span className="pbar__seg pbar__seg--missing" style={{ width: pct(d.missing_points_max, semMax) }} />}
          {d.remaining_points_max > 0 && <span className="pbar__seg pbar__seg--remaining" style={{ width: pct(d.remaining_points_max, semMax) }} />}
        </div>
        {isExam && (
          <div className="sbar__part sbar__part--exam" style={{ width: pct(examMax, total) }}>
            {examRes != null ? (
              <span className="pbar__seg pbar__seg--earned" style={{ width: pct(examRes, examMax) }} />
            ) : (
              <span className="pbar__seg sbar__seg--exam" style={{ width: '100%' }} />
            )}
            <span className="sbar__min" style={{ left: pct(examMin, examMax) }} aria-hidden="true" />
          </div>
        )}
      </div>
      <div className="sbar__captions" aria-hidden="true">
        <span style={{ width: pct(semMax, total) }}>
          Семестр <b className="num">{fmtNum(earned)}</b>/{fmtNum(semMax)}
        </span>
        {isExam && (
          <span style={{ width: pct(examMax, total) }} className="sbar__cap-exam">
            Экзамен {examRes != null ? <b className="num">{fmtNum(examRes)}</b> : null}
            {examRes != null ? `/${fmtNum(examMax)}` : `до ${fmtNum(examMax)}`}
          </span>
        )}
      </div>
      {legend && (
        <div className="pbar__legend" aria-hidden="true">
          <span>
            <i className="pbar__swatch" style={{ background: 'var(--tone)' }} />
            Набрано
          </span>
          {d.remaining_points_max > 0 && (
            <span>
              <i className="pbar__swatch pbar__seg--remaining" />
              Можно добрать в семестре
            </span>
          )}
          {isExam && examRes == null && (
            <span>
              <i className="pbar__swatch sbar__seg--exam" />
              Только на экзамене (мин. {fmtNum(examMin)})
            </span>
          )}
          {d.missing_points_max > 0 && (
            <span>
              <i className="pbar__swatch pbar__seg--missing" />
              Нет данных
            </span>
          )}
        </div>
      )}
    </div>
  );
}
