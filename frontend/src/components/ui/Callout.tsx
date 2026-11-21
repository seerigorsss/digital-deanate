import type { ReactNode } from 'react';
import { Info } from 'lucide-react';

interface CalloutProps {
  tone?: string;
  icon?: ReactNode;
  title?: ReactNode;
  children?: ReactNode;
  role?: 'status' | 'alert';
  className?: string;
}

export function Callout({ tone = 'accent', icon, title, children, role, className }: CalloutProps) {
  return (
    <div className={`callout tone-${tone} ${className ?? ''}`} role={role}>
      {icon ?? <Info aria-hidden="true" />}
      <div className="callout__body">
        {title && <div className="callout__title">{title}</div>}
        {children}
      </div>
    </div>
  );
}
