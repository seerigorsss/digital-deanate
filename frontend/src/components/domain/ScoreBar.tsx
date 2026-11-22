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

const clamp = (v: number) => Math.max(0, Math.min(100, v));
const P = (v: number) => `${clamp(v)}%`;

/**
 * Шкала итога дисциплины на единой оси 0–100 баллов:
 * набрано → можно добрать в семестре → (для экзамена) можно получить на экзамене → недоступно.
 * Под шкалой — потолок семестра и максимально возможный итог; на оси — отметки оценок 60, 71, 85.
 */
export function ScoreBar({ d, tone, size = 'md', legend = false }: { d: ScoreData; tone: string; size?: 'sm' | 'md'; legend?: boolean }) {
  const isExam = d.assessment_type === 'exam';
  const scale = isExam ? 1 : 100 / (d.semester_points_max || 100); // зачёт/распределённый экзамен: семестр = вся ось
  const examMax = isExam ? (d.exam?.points_max ?? 30) : 0;
  const examRes = isExam ? (d.exam?.result ?? null) : null;

  const earned = d.current_semester_points * scale;
  const missing = d.missing_points_max * scale;
  const remaining = d.remaining_points_max * scale;
  const semCap = earned + missing + remaining; // максимум, которого можно достичь за семестр
  const examEarned = examRes ?? 0;
  const examLeft = examRes != null ? 0 : examMax;
  const finalMax = semCap + examEarned + examLeft;
  const grades = d.assessment_type === 'credit' ? [60] : [60, 71, 85];

  const labels: { v: number; text: string; cls: string }[] = [];
  if (isExam && examRes == null) labels.push({ v: semCap, text: fmtNum(Math.round(semCap * 10) / 10), cls: 'sbar__lbl--cap' });
  labels.push({ v: finalMax, text: fmtNum(Math.round(finalMax * 10) / 10), cls: 'sbar__lbl--end' });
  // если подписи слишком близко — оставляем только итоговый максимум
  const shown = labels.length === 2 && Math.abs(labels[1].v - labels[0].v) < 9 ? [labels[1]] : labels;

  const aria =
    `Набрано ${fmtNum(d.current_semester_points)}` +
    (isExam ? ` из ${fmtNum(d.semester_points_max)} семестровых` : ` из ${fmtNum(d.semester_points_max)}`) +
    `; за семестр можно достичь ${fmtNum(Math.round(semCap * 10) / 10)}` +
    (isExam ? `; с экзаменом — до ${fmtNum(Math.round(finalMax * 10) / 10)} из 100 (на экзамене минимум 18)` : '') +
    `; отметки оценок: ${grades.join(', ')}`;

  return (
    <div className={`sbar ${size === 'sm' ? 'sbar--sm' : ''} tone-${tone}`}>
      <div className="sbar__track" role="img" aria-label={aria}>
        <span className="sbar__seg pbar__seg--earned" style={{ left: 0, width: P(earned) }} />
        {missing > 0 && <span className="sbar__seg pbar__seg--missing" style={{ left: P(earned), width: P(missing) }} />}
        {remaining > 0 && <span className="sbar__seg pbar__seg--remaining" style={{ left: P(earned + missing), width: P(remaining) }} />}
        {isExam && examEarned > 0 && <span className="sbar__seg pbar__seg--earned sbar__seg--exam-earned" style={{ left: P(semCap), width: P(examEarned) }} />}
        {isExam && examLeft > 0 && <span className="sbar__seg sbar__seg--exam" style={{ left: P(semCap), width: P(Math.min(examLeft, 100 - semCap)) }} />}
        {grades.map((g) => (
          <span key={g} className="sbar__tick" style={{ left: P(g) }} />
        ))}
      </div>
      <div className="sbar__labels" aria-hidden="true">
        {shown.map((l) => (
          <span
            key={l.cls}
            className={`sbar__lbl ${l.cls}`}
            style={clamp(l.v) > 94 ? { right: 0 } : clamp(l.v) < 6 ? { left: 0 } : { left: P(l.v), transform: 'translateX(-50%)' }}
          >
            {l.text}
          </span>
        ))}
      </div>
      {legend && (
        <div className="pbar__legend" aria-hidden="true">
          <span>
            <i className="pbar__swatch" style={{ background: 'var(--tone)' }} />
            Набрано
          </span>
          {remaining > 0 && (
            <span>
              <i className="pbar__swatch pbar__seg--remaining" />
              Можно добрать в семестре
            </span>
          )}
          {isExam && examLeft > 0 && (
            <span>
              <i className="pbar__swatch sbar__seg--exam" />
              На экзамене (мин. 18 из 30)
            </span>
          )}
          {missing > 0 && (
            <span>
              <i className="pbar__swatch pbar__seg--missing" />
              Нет данных
            </span>
          )}
          <span>
            <i className="sbar__tick-swatch" />
            Пороги оценок 60 · 71 · 85
          </span>
        </div>
      )}
    </div>
  );
}
