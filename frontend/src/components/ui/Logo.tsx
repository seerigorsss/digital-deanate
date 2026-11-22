import { Link } from 'react-router-dom';

/** Собственный знак: арка-проём («вход в учебную жизнь») и точка с дугами радара. Не копирует символику вузов. */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 32 32" aria-hidden="true" focusable="false">
      <rect width="32" height="32" rx="9" fill="#3b44d1" />
      <path d="M8.5 25V14.5a7.5 7.5 0 0 1 15 0V25" fill="none" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" />
      <circle cx="13.6" cy="21.2" r="1.9" fill="#fff" />
      <path
        d="M13.6 17.4a3.8 3.8 0 0 1 3.8 3.8M13.6 14.3a6.9 6.9 0 0 1 6.9 6.9"
        fill="none"
        stroke="#fff"
        strokeWidth="1.9"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function Logo({ to = '/', tag = 'концепт для конкурса', compact }: { to?: string; tag?: string; compact?: boolean }) {
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
