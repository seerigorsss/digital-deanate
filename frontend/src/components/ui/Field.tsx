import { useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react';
import { CircleAlert } from 'lucide-react';

interface FieldShellProps {
  id: string;
  label: ReactNode;
  required?: boolean;
  hint?: ReactNode;
  error?: string | null;
  counter?: ReactNode;
  children: ReactNode;
  className?: string;
}

/** Обёртка поля: подпись, подсказка, ошибка (связаны aria-describedby). */
export function FieldShell({ id, label, required, hint, error, counter, children, className }: FieldShellProps) {
  return (
    <div className={`field ${className ?? ''}`}>
      <label className="field__label" htmlFor={id}>
        {label}
        {required && (
          <span className="field__req" aria-hidden="true">
            *
          </span>
        )}
      </label>
      {children}
      {(hint || counter) && !error && (
        <div className="field__foot">
          <span className="field__hint" id={`${id}-hint`}>
            {hint}
          </span>
          {counter && <span className="field__hint num">{counter}</span>}
        </div>
      )}
      {error && (
        <div className="field__error" id={`${id}-error`} role="alert">
          <CircleAlert aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}

function describedBy(id: string, hint: unknown, error: unknown, counter?: unknown): string | undefined {
  if (error) return `${id}-error`;
  if (hint || counter) return `${id}-hint`;
  return undefined;
}

interface BaseFieldProps {
  label: ReactNode;
  hint?: ReactNode;
  error?: string | null;
  showCounter?: boolean;
}

export function TextField({ label, hint, error, required, id, className, ...rest }: BaseFieldProps & InputHTMLAttributes<HTMLInputElement>) {
  const auto = useId();
  const fid = id ?? auto;
  return (
    <FieldShell id={fid} label={label} required={required} hint={hint} error={error} className={className}>
      <input
        id={fid}
        className="input"
        required={required}
        aria-required={required || undefined}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(fid, hint, error)}
        {...rest}
      />
    </FieldShell>
  );
}

export function TextAreaField({
  label,
  hint,
  error,
  required,
  id,
  showCounter,
  className,
  ...rest
}: BaseFieldProps & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const auto = useId();
  const fid = id ?? auto;
  const len = typeof rest.value === 'string' ? rest.value.length : 0;
  const counter = showCounter && rest.maxLength ? `${len} / ${rest.maxLength}` : undefined;
  return (
    <FieldShell id={fid} label={label} required={required} hint={hint} error={error} counter={counter} className={className}>
      <textarea
        id={fid}
        className="textarea"
        required={required}
        aria-required={required || undefined}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(fid, hint, error, counter)}
        {...rest}
      />
    </FieldShell>
  );
}

export function SelectField({
  label,
  hint,
  error,
  required,
  id,
  className,
  children,
  ...rest
}: BaseFieldProps & SelectHTMLAttributes<HTMLSelectElement>) {
  const auto = useId();
  const fid = id ?? auto;
  return (
    <FieldShell id={fid} label={label} required={required} hint={hint} error={error} className={className}>
      <select
        id={fid}
        className="select"
        required={required}
        aria-required={required || undefined}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(fid, hint, error)}
        {...rest}
      >
        {children}
      </select>
    </FieldShell>
  );
}
