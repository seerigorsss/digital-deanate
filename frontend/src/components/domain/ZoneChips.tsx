import type { RiskLevel, ZoneCounts } from '../../api/types';
import { RISK_META, RISK_ORDER } from '../../lib/semantics';

interface Props {
  counts: ZoneCounts;
  /** Если передан — чипы становятся фильтром */
  active?: RiskLevel | null;
  onSelect?: (level: RiskLevel | null) => void;
}

/** Число дисциплин по зонам риска — только ненулевые, в порядке тяжести. */
export function ZoneChips({ counts, active, onSelect }: Props) {
  const levels = RISK_ORDER.filter((l) => (counts[l] ?? 0) > 0);
  return (
    <ul className="zone-chips" aria-label="Дисциплины по зонам риска">
      {levels.map((l) => {
        const meta = RISK_META[l];
        const Icon = meta.icon;
        const n = counts[l];
        const content = (
          <>
            <Icon aria-hidden="true" />
            <span>{l === 'insufficient_data' ? 'Нет данных' : meta.label}</span>
            <strong className="num">{n}</strong>
          </>
        );
        return (
          <li key={l}>
            {onSelect ? (
              <button
                type="button"
                className={`zone-chip tone-${meta.tone}`}
                aria-pressed={active === l}
                onClick={() => onSelect(active === l ? null : l)}
              >
                {content}
              </button>
            ) : (
              <span className={`zone-chip tone-${meta.tone}`}>{content}</span>
            )}
          </li>
        );
      })}
    </ul>
  );
}
