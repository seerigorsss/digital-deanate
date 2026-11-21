import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { Link, type LinkProps } from 'react-router-dom';
import { LoaderCircle } from 'lucide-react';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'default' | 'danger' | 'danger-solid';

interface CommonProps {
  variant?: ButtonVariant;
  size?: 'md' | 'sm';
  block?: boolean;
  icon?: ReactNode;
  iconRight?: ReactNode;
  wrap?: boolean;
}

function cls(variant: ButtonVariant, size: 'md' | 'sm', block?: boolean, wrap?: boolean, extra?: string): string {
  return [
    'btn',
    variant !== 'default' ? `btn--${variant}` : '',
    size === 'sm' ? 'btn--sm' : '',
    block ? 'btn--block' : '',
    wrap ? 'btn--wrap' : '',
    extra ?? '',
  ]
    .filter(Boolean)
    .join(' ');
}

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>, CommonProps {
  loading?: boolean;
  loadingText?: string;
}

/** Кнопка: варианты, состояние загрузки (блокирует повторное нажатие), disabled. */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'default', size = 'md', block, icon, iconRight, loading, loadingText, wrap, className, children, disabled, type, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type ?? 'button'}
      className={cls(variant, size, block, wrap, `${loading ? 'btn--loading' : ''} ${className ?? ''}`)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? <LoaderCircle className="btn__spinner" aria-hidden="true" /> : icon}
      {children !== undefined && <span className="btn__label">{loading && loadingText ? loadingText : children}</span>}
      {!loading && iconRight}
    </button>
  );
});

export interface ButtonLinkProps extends LinkProps, CommonProps {}

export function ButtonLink({ variant = 'default', size = 'md', block, icon, iconRight, wrap, className, children, ...rest }: ButtonLinkProps) {
  return (
    <Link className={cls(variant, size, block, wrap, className)} {...rest}>
      {icon}
      <span className="btn__label">{children}</span>
      {iconRight}
    </Link>
  );
}

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
  bordered?: boolean;
}

/** Кнопка-иконка: обязательная подпись для экранного диктора, зона касания 44×44. */
export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { label, bordered, className, children, type, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type ?? 'button'}
      className={`icon-btn ${bordered ? 'icon-btn--bordered' : ''} ${className ?? ''}`}
      aria-label={label}
      title={label}
      {...rest}
    >
      {children}
    </button>
  );
});
