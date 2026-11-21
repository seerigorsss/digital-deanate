import type { ReactNode } from 'react';
import type { ApplicationStatus, IndexZone, RiskLevel, TargetStatus } from '../../api/types';
import { RISK_META, STATUS_META, TARGET_META, ZONE_META } from '../../lib/semantics';

type Size = 'sm' | 'md' | 'lg';

interface BadgeProps {
  tone?: string;
  size?: Size;
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
  title?: string;
  variant?: 'plain' | 'outline';
}

export function Badge({ tone, size = 'sm', icon, children, className, title, variant }: BadgeProps) {
  const classes = [
    'badge',
    tone ? `tone-${tone}` : '',
    size !== 'sm' ? `badge--${size}` : '',
    variant ? `badge--${variant}` : '',
    className ?? '',
  ]
    .filter(Boolean)
    .join(' ');
  return (
    <span className={classes} title={title}>
      {icon}
      {children}
    </span>
  );
}

/** Уровень риска: цвет + иконка + текст (цвет никогда не единственный носитель смысла). */
export function RiskBadge({ level, label, size = 'sm' }: { level: RiskLevel; label?: string; size?: Size }) {
  const meta = RISK_META[level] ?? RISK_META.insufficient_data;
  const Icon = meta.icon;
  return (
    <Badge tone={meta.tone} size={size} icon={<Icon aria-hidden="true" />}>
      {label || meta.label}
    </Badge>
  );
}

export function ZoneBadge({ zone, label, size = 'sm' }: { zone: IndexZone | null; label?: string | null; size?: Size }) {
  if (!zone) {
    return <RiskBadge level="insufficient_data" size={size} />;
  }
  const meta = ZONE_META[zone];
  const Icon = meta.icon;
  return (
    <Badge tone={meta.tone} size={size} icon={<Icon aria-hidden="true" />}>
      {label || meta.label}
    </Badge>
  );
}

export function StatusPill({ status, label, size = 'sm' }: { status: ApplicationStatus; label?: string; size?: Size }) {
  const meta = STATUS_META[status] ?? STATUS_META.draft;
  const Icon = meta.icon;
  return (
    <Badge tone={meta.tone} size={size} icon={<Icon aria-hidden="true" />}>
      {label || meta.label}
    </Badge>
  );
}

export function TargetBadge({ status, label }: { status: TargetStatus; label?: string }) {
  const meta = TARGET_META[status] ?? TARGET_META.unknown;
  const Icon = meta.icon;
  return (
    <Badge tone={meta.tone} icon={<Icon aria-hidden="true" />}>
      {label ?? meta.label}
    </Badge>
  );
}
