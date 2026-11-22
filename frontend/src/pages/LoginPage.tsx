import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom';
import { BellRing, CalendarDays, Eye, EyeOff, FileText, GraduationCap, LogIn } from 'lucide-react';
import { ApiError } from '../api/client';
import { useMeta } from '../api/hooks';
import { homePathFor, useAuth } from '../auth/AuthContext';
import { DisclaimerBar } from '../components/layout/AppShell';
import { Button } from '../components/ui/Button';
import { Callout } from '../components/ui/Callout';
import { FieldShell } from '../components/ui/Field';
import { LogoMark } from '../components/ui/Logo';
import { useDocumentTitle } from '../components/ui/PageHeader';
import type { User } from '../api/types';

const DEMO = [
  { login: 'student1', who: 'студент' },
  { login: 'student2', who: 'студент' },
  { login: 'dekanat', who: 'сотрудник деканата' },
];

/** Безопасный next: только внутренний путь, доступный роли. */
function safeNext(next: string | null, user: User): string {
  const home = homePathFor(user);
  if (!next || !next.startsWith('/') || next.startsWith('//') || next.startsWith('/login')) return home;
  const isStaffPath = next.startsWith('/staff');
  if (user.role === 'staff' && !isStaffPath) return home;
  if (user.role === 'student' && isStaffPath) return home;
  return next;
}

export function LoginPage() {
  useDocumentTitle('Вход');
  const { user, status, login } = useAuth();
  const meta = useMeta();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [form, setForm] = useState({ login: '', password: '' });
  const [errors, setErrors] = useState<{ login?: string; password?: string }>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const loginRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);
  const expired = params.get('expired') === '1';

  useEffect(() => {
    loginRef.current?.focus();
  }, []);

  if (status === 'authenticated' && user && !submitting) {
    return <Navigate to={safeNext(params.get('next'), user)} replace />;
  }

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const errs: typeof errors = {};
    if (!form.login.trim()) errs.login = 'Введите логин';
    if (!form.password) errs.password = 'Введите пароль';
    setErrors(errs);
    setFormError(null);
    if (errs.login) return loginRef.current?.focus();
    if (errs.password) return passwordRef.current?.focus();
    setSubmitting(true);
    try {
      const u = await login(form.login.trim(), form.password);
      navigate(safeNext(params.get('next'), u), { replace: true });
    } catch (err) {
      setSubmitting(false);
      setForm((f) => ({ ...f, password: '' }));
      if (err instanceof ApiError) {
        if (err.status === 401) setFormError('Неверный логин или пароль. Проверьте раскладку клавиатуры и Caps Lock.');
        else if (err.status === 429) setFormError('Слишком много попыток входа. Подождите несколько минут и попробуйте снова.');
        else if (err.isNetwork) setFormError('Не удалось связаться с сервером. Проверьте интернет и попробуйте ещё раз.');
        else setFormError(err.message);
      } else {
        setFormError('Не удалось войти. Попробуйте ещё раз.');
      }
      passwordRef.current?.focus();
    }
  };

  return (
    <div className="auth-page">
      <DisclaimerBar />
      <main className="auth-wrap" id="main">
        <div className="auth-grid">
          <section className="auth-intro" aria-label="О сервисе">
            <LogoMark className="logo__mark" />
            <h2 className="auth-intro__title">Цифровой деканат будущего</h2>
            <p className="text-2" style={{ fontSize: 'var(--fs-lg)', maxWidth: '42ch' }}>
              Всё, что нужно студенту, в одном кабинете — с телефона и без очереди в деканат.
            </p>
            <ul className="auth-intro__list">
              <li>
                <CalendarDays aria-hidden="true" />
                <span>Расписание на день и неделю — с заметными отменами и переносами</span>
              </li>
              <li>
                <GraduationCap aria-hidden="true" />
                <span>Академический радар: что подтянуть и сколько баллов ещё нужно</span>
              </li>
              <li>
                <FileText aria-hidden="true" />
                <span>Справки и заявления онлайн — со статусом и подсказкой «что дальше»</span>
              </li>
              <li>
                <BellRing aria-hidden="true" />
                <span>Объявления, сроки и изменения — в уведомлениях</span>
              </li>
            </ul>
          </section>

          <div className="card auth-card">
            <div className="stack">
              <div className="row" style={{ gap: 12 }}>
                <LogoMark className="logo__mark" />
                <div>
                  <div className="strong">Цифровой деканат</div>
                  <div className="xsmall muted">{meta.data?.university_name ?? 'концепт для конкурса'}</div>
                </div>
              </div>
              <div>
                <h1 className="page-title" id="page-title" tabIndex={-1}>
                  Вход в кабинет
                </h1>
                <p className="page-subtitle">Личный кабинет студента: расписание, успеваемость, заявки и связь с деканатом</p>
              </div>

              {expired && !formError && (
                <Callout tone="attention" role="status">
                  Сессия завершилась. Войдите снова — вы вернётесь туда, где были.
                </Callout>
              )}

              <form className="stack" onSubmit={onSubmit} noValidate>
                <FieldShell id="login" label="Логин" required error={errors.login}>
                  <input
                    ref={loginRef}
                    id="login"
                    name="username"
                    className="input"
                    autoComplete="username"
                    autoCapitalize="none"
                    spellCheck={false}
                    value={form.login}
                    aria-invalid={errors.login ? true : undefined}
                    aria-describedby={errors.login ? 'login-error' : undefined}
                    aria-required="true"
                    onChange={(e) => setForm({ ...form, login: e.target.value })}
                    disabled={submitting}
                  />
                </FieldShell>
                <FieldShell id="password" label="Пароль" required error={errors.password}>
                  <div className="input-group">
                    <input
                      ref={passwordRef}
                      id="password"
                      name="password"
                      className="input"
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="current-password"
                      value={form.password}
                      aria-invalid={errors.password ? true : undefined}
                      aria-describedby={errors.password ? 'password-error' : undefined}
                      aria-required="true"
                      onChange={(e) => setForm({ ...form, password: e.target.value })}
                      disabled={submitting}
                    />
                    <button
                      type="button"
                      className="icon-btn input-group__btn"
                      aria-label={showPassword ? 'Скрыть пароль' : 'Показать пароль'}
                      aria-pressed={showPassword}
                      onClick={() => setShowPassword((v) => !v)}
                    >
                      {showPassword ? <EyeOff aria-hidden="true" /> : <Eye aria-hidden="true" />}
                    </button>
                  </div>
                </FieldShell>

                {formError && (
                  <Callout tone="danger" role="alert">
                    {formError}
                  </Callout>
                )}

                <Button type="submit" variant="primary" block loading={submitting} loadingText="Входим…" icon={<LogIn aria-hidden="true" />}>
                  Войти
                </Button>
              </form>

              <div className="callout tone-neutral">
                <div className="callout__body">
                  <div className="strong">Демо-доступ</div>
                  <div className="text-2">Нажмите на логин, чтобы подставить его. Пароли — в инструкции для жюри.</div>
                  <div className="demo-logins">
                    {DEMO.map((d) => (
                      <button
                        key={d.login}
                        type="button"
                        className="demo-login"
                        onClick={() => {
                          setForm((f) => ({ ...f, login: d.login }));
                          passwordRef.current?.focus();
                        }}
                        aria-label={`Подставить логин ${d.login} (${d.who})`}
                      >
                        <code>{d.login}</code>
                        <span>{d.who}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <p className="xsmall muted">
                {meta.data?.disclaimer ?? 'Концепт, созданный для конкурса. Не является официальным сервисом университета.'}
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
