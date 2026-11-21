import type { HTMLAttributes, ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';

interface CardProps extends HTMLAttributes<HTMLElement> {
  as?: 'section' | 'article' | 'div' | 'aside';
  flush?: boolean;
  soft?: boolean;
  tone?: string;
}

export function Card({ as = 'section', flush, soft, tone, className, children, ...rest }: CardProps) {
  const Tag = as;
  const classes = ['card', flush ? 'card--flush' : '', soft ? 'card--soft' : '', tone ? `card--tone tone-${tone}` : '', className ?? '']
    .filter(Boolean)
    .join(' ');
  return (
    <Tag className={classes} {...rest}>
      {children}
    </Tag>
  );
}

interface CardHeaderProps {
  title: ReactNode;
  icon?: ReactNode;
  id?: string;
  level?: 2 | 3;
  link?: { to: string; label: string };
  aside?: ReactNode;
}

export function CardHeader({ title, icon, id, level = 2, link, aside }: CardHeaderProps) {
  const H = level === 2 ? 'h2' : 'h3';
  return (
    <div className="card__head">
      {icon}
      <H className="card__title" id={id}>
        {title}
      </H>
      {aside}
      {link && (
        <Link className="card__link" to={link.to}>
          {link.label}
          <ChevronRight aria-hidden="true" />
        </Link>
      )}
    </div>
  );
}
