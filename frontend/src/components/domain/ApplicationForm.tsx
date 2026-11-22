import { useState, type FormEvent } from 'react';
import type { ApplicationType, FormField, Payload } from '../../api/types';
import { SelectField, TextAreaField, TextField } from '../ui/Field';
import { Button } from '../ui/Button';

export type FieldErrors = Record<string, string>;

export function initialPayload(t: ApplicationType, existing?: Payload): Record<string, string> {
  const out: Record<string, string> = {};
  for (const f of t.fields) {
    const v = existing?.[f.name] ?? f.default;
    out[f.name] = v == null ? '' : String(v);
  }
  return out;
}

/** Клиентская проверка (дублирует серверную — сервер всё равно проверяет всё сам). */
export function validateClient(t: ApplicationType, values: Record<string, string>, partial: boolean): FieldErrors {
  const errs: FieldErrors = {};
  for (const f of t.fields) {
    const v = (values[f.name] ?? '').trim();
    if (!v) {
      if (f.required && !partial) errs[f.name] = 'Заполните это поле';
      continue;
    }
    if ((f.type === 'text' || f.type === 'textarea') && !partial && f.min_length && v.length < f.min_length)
      errs[f.name] = `Минимум ${f.min_length} символов`;
    if ((f.type === 'text' || f.type === 'textarea') && f.max_length && v.length > f.max_length)
      errs[f.name] = `Максимум ${f.max_length} символов`;
    if (f.type === 'number') {
      const n = Number(v);
      if (!Number.isInteger(n)) errs[f.name] = 'Нужно целое число';
      else if ((f.min != null && n < f.min) || (f.max != null && n > f.max)) errs[f.name] = `Допустимо от ${f.min} до ${f.max}`;
    }
  }
  if (values.period_from && values.period_to && values.period_from > values.period_to)
    errs.period_to = 'Дата окончания раньше даты начала';
  return errs;
}

export function toPayload(t: ApplicationType, values: Record<string, string>): Payload {
  const out: Payload = {};
  for (const f of t.fields) {
    const v = (values[f.name] ?? '').trim();
    if (!v) continue;
    out[f.name] = f.type === 'number' || f.type === 'discipline' ? Number(v) : v;
  }
  return out;
}

function FieldInput({ f, value, error, onChange }: { f: FormField; value: string; error?: string; onChange: (v: string) => void }) {
  const common = { label: f.label, required: f.required, error: error ?? null, hint: f.hint, name: f.name };
  if (f.type === 'textarea')
    return (
      <TextAreaField
        {...common}
        value={value}
        rows={5}
        maxLength={f.max_length}
        placeholder={f.placeholder}
        showCounter={!!f.max_length}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  if (f.type === 'select' || f.type === 'discipline')
    return (
      <SelectField {...common} value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">Выберите…</option>
        {(f.options ?? []).map((o) => (
          <option key={String(o.value)} value={String(o.value)}>
            {o.label}
          </option>
        ))}
      </SelectField>
    );
  if (f.type === 'number')
    return (
      <TextField
        {...common}
        type="number"
        inputMode="numeric"
        min={f.min}
        max={f.max}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  if (f.type === 'date') return <TextField {...common} type="date" value={value} onChange={(e) => onChange(e.target.value)} />;
  return (
    <TextField
      {...common}
      value={value}
      maxLength={f.max_length}
      placeholder={f.placeholder}
      autoComplete="off"
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

interface Props {
  type: ApplicationType;
  initial?: Payload;
  busy?: 'submit' | 'draft' | null;
  serverErrors?: FieldErrors;
  submitLabel?: string;
  draftLabel?: string;
  onSubmit: (payload: Payload, submit: boolean) => void;
  onCancel?: () => void;
}

export function ApplicationForm({ type, initial, busy, serverErrors, submitLabel = 'Отправить', draftLabel = 'Сохранить черновик', onSubmit, onCancel }: Props) {
  const [values, setValues] = useState<Record<string, string>>(() => initialPayload(type, initial));
  const [errors, setErrors] = useState<FieldErrors>({});
  const shown = { ...serverErrors, ...errors };

  const run = (submit: boolean) => {
    const errs = validateClient(type, values, !submit);
    setErrors(errs);
    if (Object.keys(errs).length) {
      const first = type.fields.find((f) => errs[f.name]);
      if (first) document.querySelector<HTMLElement>(`[name="${first.name}"]`)?.focus();
      return;
    }
    onSubmit(toPayload(type, values), submit);
  };
  const handle = (e: FormEvent) => {
    e.preventDefault();
    run(true);
  };

  return (
    <form className="stack" onSubmit={handle} noValidate>
      {type.fields.map((f) => (
        <FieldInput
          key={f.name}
          f={f}
          value={values[f.name] ?? ''}
          error={shown[f.name]}
          onChange={(v) => {
            setValues((s) => ({ ...s, [f.name]: v }));
            if (errors[f.name]) setErrors(({ [f.name]: _, ...rest }) => rest);
          }}
        />
      ))}
      <div className="row-wrap">
        <Button type="submit" variant="primary" loading={busy === 'submit'} disabled={!!busy}>
          {submitLabel}
        </Button>
        <Button type="button" variant="secondary" loading={busy === 'draft'} disabled={!!busy} onClick={() => run(false)}>
          {draftLabel}
        </Button>
        {onCancel && (
          <Button type="button" variant="ghost" disabled={!!busy} onClick={onCancel}>
            Отмена
          </Button>
        )}
      </div>
      <p className="xsmall muted">Поля со звёздочкой обязательны. Черновик видите только вы — деканат получит заявку после отправки.</p>
    </form>
  );
}
