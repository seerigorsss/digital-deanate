import { Link } from 'react-router-dom';

/** Собственный знак: шапка выпускника + «цифровые» пиксели на кисточке. Не копирует символику вузов. */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 32 32" aria-hidden="true" focusable="false">
      <defs>
        <linearGradient id="dd-logo-g" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#6366f1" />
          <stop offset="1" stopColor="#4338ca" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="9" fill="url(#dd-logo-g)" />
      <path d="M16 6.5 27 12l-11 5.5L5 12z" fill="#fff" />
      <path d="M9.5 14.8v4.6c0 1.9 2.9 3.6 6.5 3.6s6.5-1.7 6.5-3.6v-4.6L16 18z" fill="#fff" fillOpacity=".78" />
      <path d="M26.2 12.6v5.4" stroke="#fff" strokeWidth="1.4" strokeLinecap="round" />
      <rect x="24.9" y="19.2" width="2.6" height="2.6" rx=".6" fill="#a5f3fc" />
      <rect x="24.9" y="23" width="2.6" height="2.6" rx=".6" fill="#a5f3fc" fillOpacity=".6" />
    </svg>
  );
}

export function Logo({ to = '/', tag = 'концепт', compact }: { to?: string; tag?: string; compact?: boolean }) {
  return (
    <Link to={to} className="logo" aria-label="Цифровой деканат — на главную">
      <LogoMark className="logo__mark" />
      {!compact && (
        <span className="logo__text">
          <span className="logo__name">Цифровой деканат</span>
          <span className="logo__tag">{tag}</span>
        </span>
      )}
    </Link>
  );
}
