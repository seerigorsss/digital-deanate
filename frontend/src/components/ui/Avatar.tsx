export function Avatar({ initials, size = 'md', staff }: { initials: string; size?: 'sm' | 'md' | 'lg'; staff?: boolean }) {
  return (
    <span className={`avatar ${size !== 'md' ? `avatar--${size}` : ''} ${staff ? 'avatar--staff' : ''}`} aria-hidden="true">
      {initials}
    </span>
  );
}
