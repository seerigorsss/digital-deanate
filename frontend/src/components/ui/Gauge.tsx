import type { IndexZone } from '../../api/types';

interface GaugeProps {
  value: number | null;
  max?: number;
  zone: IndexZone | null;
  label?: string | null;
  size?: 'md' | 'sm';
}

const ZONES: { from: number; to: number; tone: IndexZone }[] = [
  { from: 0, to: 50, tone: 'critical' },
  { from: 50, to: 65, tone: 'high' },
  { from: 65, to: 80, tone: 'medium' },
  { from: 80, to: 100, tone: 'stable' },
];

const CX = 100;
const CY = 100;

function point(v: number, r: number): [number, number] {
  const t = Math.PI * (1 - Math.max(0, Math.min(100, v)) / 100);
  return [CX + r * Math.cos(t), CY - r * Math.sin(t)];
}

function arc(from: number, to: number, r: number): string {
  const [x1, y1] = point(from, r);
  const [x2, y2] = point(to, r);
  return `M ${x1.toFixed(2)} ${y1.toFixed(2)} A ${r} ${r} 0 0 1 ${x2.toFixed(2)} ${y2.toFixed(2)}`;
}

/**
 * Полукруглая шкала индекса 0–100. Внешнее тонкое кольцо — границы зон, основная дуга — значение.
 * Смысл дублируется текстом (значение + подпись зоны рядом) и aria-label.
 */
export function Gauge({ value, max = 100, zone, label, size = 'md' }: GaugeProps) {
  const v = value === null ? null : (value / max) * 100;
  const tone = zone ?? 'nodata';
  const aria = value === null ? 'Индекс не рассчитан: недостаточно данных' : `Индекс ${value} из ${max}${label ? `, зона «${label}»` : ''}`;
  const knob = v !== null ? point(v, 80) : null;
  return (
    <div className={`gauge ${size === 'sm' ? 'gauge--sm' : ''} tone-${tone}`} role="img" aria-label={aria}>
      <svg viewBox="0 0 200 112" aria-hidden="true" focusable="false">
        {ZONES.map((z) => (
          <path
            key={z.tone}
            d={arc(z.from + 0.6, z.to - 0.6, 96)}
            fill="none"
            stroke={`var(--c-${z.tone})`}
            strokeOpacity={0.55}
            strokeWidth={4}
            strokeLinecap="round"
          />
        ))}
        <path d={arc(0, 100, 80)} fill="none" stroke="var(--c-surface-3)" strokeWidth={16} strokeLinecap="round" />
        {v !== null && v > 0 && (
          <path d={arc(0, v, 80)} fill="none" stroke="var(--tone)" strokeWidth={16} strokeLinecap="round" />
        )}
        {knob && <circle cx={knob[0]} cy={knob[1]} r={10} fill="#fff" stroke="var(--tone)" strokeWidth={4} />}
      </svg>
      <div className="gauge__value">
        <span className="gauge__number">{value === null ? '—' : value}</span>
        <span className="gauge__max">/{max}</span>
      </div>
    </div>
  );
}
