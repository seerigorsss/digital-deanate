import { fmtNum } from '../../lib/format';

export interface BarMark {
  value: number;
  label: string;
}

interface PointsBarProps {
  max: number;
  earned: number;
  remaining?: number;
  missing?: number;
  marks?: BarMark[];
  tone?: string;
  size?: 'md' | 'sm';
  legend?: boolean;
  label?: string;
}

const pct = (v: number, max: number) => `${Math.max(0, Math.min(100, (v / max) * 100))}%`;

/**
 * Полоса баллов: набрано (цвет зоны) · ещё можно набрать (штриховка акцента) · нет данных (серая штриховка),
 * вертикальные отметки порогов. Пустой остаток справа — баллы, которые уже недоступны.
 */
export function PointsBar({ max, earned, remaining = 0, missing = 0, marks = [], tone = 'accent', size = 'md', legend, label }: PointsBarProps) {
  const safeMax = max > 0 ? max : 1;
  const aria =
    label ??
    `Набрано ${fmtNum(earned)} из ${fmtNum(max)}` +
      (remaining > 0 ? `, ещё можно набрать ${fmtNum(remaining)}` : '') +
      (missing > 0 ? `, нет данных по ${fmtNum(missing)}` : '') +
      (marks.length ? `; отметки: ${marks.map((m) => m.label).join(', ')}` : '');
  return (
    <div className={`pbar ${size === 'sm' ? 'pbar--sm' : ''} tone-${tone}`}>
      <div className="pbar__track" role="img" aria-label={aria}>
        <span className="pbar__seg pbar__seg--earned" style={{ width: pct(earned, safeMax) }} />
        {missing > 0 && <span className="pbar__seg pbar__seg--missing" style={{ width: pct(missing, safeMax) }} />}
        {remaining > 0 && <span className="pbar__seg pbar__seg--remaining" style={{ width: pct(remaining, safeMax) }} />}
      </div>
      {marks.length > 0 && (
        <div className="pbar__marks" aria-hidden="true">
          {marks.map((m) => (
            <span key={`${m.value}-${m.label}`} className="pbar__mark" style={{ left: pct(m.value, safeMax) }} />
          ))}
        </div>
      )}
      {marks.length > 0 && size !== 'sm' && (
        <div className="pbar__labels" aria-hidden="true">
          {marks.map((m) => {
            const p = (m.value / safeMax) * 100;
            const style =
              p < 8 ? { left: 0, transform: 'none' } : p > 92 ? { right: 0, left: 'auto', transform: 'none' } : { left: `${p}%` };
            return (
              <span key={`${m.value}-${m.label}`} className="pbar__mark-label" style={style}>
                {m.label}
              </span>
            );
          })}
        </div>
      )}
      {legend && (
        <div className="pbar__legend" aria-hidden="true">
          <span>
            <i className="pbar__swatch" style={{ background: 'var(--tone)' }} />
            Набрано
          </span>
          {remaining > 0 && (
            <span>
              <i className="pbar__swatch pbar__seg--remaining" />
              Ещё можно набрать
            </span>
          )}
          {missing > 0 && (
            <span>
              <i className="pbar__swatch pbar__seg--missing" />
              Нет данных
            </span>
          )}
          {earned + remaining + missing < max && (
            <span>
              <i className="pbar__swatch" style={{ background: 'var(--c-surface-3)', border: '1px solid var(--c-border-strong)' }} />
              Уже недоступно
            </span>
          )}
        </div>
      )}
    </div>
  );
}
