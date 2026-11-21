/** Форматирование дат, чисел и склонений. Время показываем в Europe/Moscow (контракт API). */

const TZ = 'Europe/Moscow';

const MONTHS_GEN = [
  'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря',
];
const MONTHS_NOM = [
  'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь',
];
const WEEKDAYS = ['Воскресенье', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота'];
const WEEKDAYS_SHORT = ['вс', 'пн', 'вт', 'ср', 'чт', 'пт', 'сб'];

/** 'YYYY-MM-DD' → Date в полдень UTC (без сдвигов из-за часовых поясов). */
export function parseISODate(iso: string): Date {
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number);
  return new Date(Date.UTC(y, (m || 1) - 1, d || 1, 12));
}

export function toISODate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export function addDays(iso: string, days: number): string {
  const d = parseISODate(iso);
  d.setUTCDate(d.getUTCDate() + days);
  return toISODate(d);
}

/** Понедельник недели, в которую попадает дата. */
export function mondayOf(iso: string): string {
  const d = parseISODate(iso);
  const wd = (d.getUTCDay() + 6) % 7;
  return addDays(iso, -wd);
}

export function daysBetween(fromIso: string, toIso: string): number {
  return Math.round((parseISODate(toIso).getTime() - parseISODate(fromIso).getTime()) / 86_400_000);
}

export function isValidISODate(s: string | null | undefined): s is string {
  if (!s || !/^\d{4}-\d{2}-\d{2}$/.test(s)) return false;
  const d = parseISODate(s);
  return !Number.isNaN(d.getTime()) && toISODate(d) === s;
}

/** 23 ноября */
export function formatDay(iso: string): string {
  const d = parseISODate(iso);
  return `${d.getUTCDate()} ${MONTHS_GEN[d.getUTCMonth()]}`;
}

/** 23 ноября 2026 */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = parseISODate(iso);
  return `${d.getUTCDate()} ${MONTHS_GEN[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

/** 23.11.2026 */
export function formatDateNumeric(iso: string | null | undefined): string {
  if (!iso) return '—';
  const [y, m, d] = iso.slice(0, 10).split('-');
  return `${d}.${m}.${y}`;
}

/** Понедельник */
export function weekdayName(iso: string): string {
  return WEEKDAYS[parseISODate(iso).getUTCDay()];
}

/** пн */
export function weekdayShort(iso: string): string {
  return WEEKDAYS_SHORT[parseISODate(iso).getUTCDay()];
}

export function dayOfMonth(iso: string): number {
  return parseISODate(iso).getUTCDate();
}

export function monthName(iso: string): string {
  return MONTHS_NOM[parseISODate(iso).getUTCMonth()];
}

/** «23–29 ноября» или «30 ноября – 6 декабря» */
export function formatRange(fromIso: string, toIso: string): string {
  const a = parseISODate(fromIso);
  const b = parseISODate(toIso);
  if (a.getUTCMonth() === b.getUTCMonth()) {
    return `${a.getUTCDate()}–${b.getUTCDate()} ${MONTHS_GEN[b.getUTCMonth()]}`;
  }
  return `${formatDay(fromIso)} – ${formatDay(toIso)}`;
}

/** ISO дата-время без зоны трактуется как UTC. */
export function parseDateTime(iso: string): Date {
  const hasZone = /([zZ]|[+-]\d{2}:?\d{2})$/.test(iso);
  return new Date(hasZone ? iso : `${iso}Z`);
}

const dtFormatter = new Intl.DateTimeFormat('ru-RU', {
  timeZone: TZ,
  day: 'numeric',
  month: 'long',
  hour: '2-digit',
  minute: '2-digit',
});
const dtYearFormatter = new Intl.DateTimeFormat('ru-RU', {
  timeZone: TZ,
  day: 'numeric',
  month: 'long',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
});
const dateOnlyFormatter = new Intl.DateTimeFormat('ru-RU', { timeZone: TZ, day: 'numeric', month: 'long' });
const isoDayFormatter = new Intl.DateTimeFormat('en-CA', { timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit' });
const hourFormatter = new Intl.DateTimeFormat('ru-RU', { timeZone: TZ, hour: 'numeric', hour12: false });

/** «20 ноября, 12:15» (в Москве) */
export function formatDateTime(iso: string | null | undefined, withYear = false): string {
  if (!iso) return '—';
  const d = parseDateTime(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return (withYear ? dtYearFormatter : dtFormatter).format(d).replace(' в ', ', ');
}

/** Дата события в Москве — 'YYYY-MM-DD' */
export function dateTimeToISODay(iso: string): string {
  return isoDayFormatter.format(parseDateTime(iso));
}

/** «20 ноября» / «сегодня» / «вчера» относительно серверного «сегодня». */
export function formatRelativeDay(iso: string, today: string | undefined): string {
  const day = dateTimeToISODay(iso);
  if (today) {
    const diff = daysBetween(day, today);
    if (diff === 0) return 'сегодня';
    if (diff === 1) return 'вчера';
  }
  return dateOnlyFormatter.format(parseDateTime(iso));
}

export function moscowHour(): number {
  return Number(hourFormatter.format(new Date()));
}

export function plural(n: number, forms: [string, string, string]): string {
  const abs = Math.abs(Math.trunc(n));
  const n10 = abs % 10;
  const n100 = abs % 100;
  if (!Number.isInteger(n)) return forms[1];
  if (n10 === 1 && n100 !== 11) return forms[0];
  if (n10 >= 2 && n10 <= 4 && (n100 < 12 || n100 > 14)) return forms[1];
  return forms[2];
}

const numFmt = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 1 });

/** 27 → «27», 38.57 → «38,6» */
export function fmtNum(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return '—';
  return numFmt.format(n);
}

export function fmtPoints(n: number | null | undefined): string {
  if (n === null || n === undefined) return '—';
  return `${fmtNum(n)} ${plural(n, ['балл', 'балла', 'баллов'])}`;
}

export function fmtPercent(share: number | null | undefined): string {
  if (share === null || share === undefined) return '—';
  return `${Math.round(share * 100)}%`;
}

/** «через 3 дня», «сегодня», «завтра», «2 дня назад» */
export function daysLeftLabel(days: number | null | undefined): string {
  if (days === null || days === undefined) return '';
  if (days === 0) return 'сегодня';
  if (days === 1) return 'завтра';
  if (days < 0) {
    const n = Math.abs(days);
    return `${n} ${plural(n, ['день', 'дня', 'дней'])} назад`;
  }
  return `через ${days} ${plural(days, ['день', 'дня', 'дней'])}`;
}

export function greeting(): string {
  const h = moscowHour();
  if (h >= 5 && h < 12) return 'Доброе утро';
  if (h >= 12 && h < 18) return 'Добрый день';
  if (h >= 18 && h < 23) return 'Добрый вечер';
  return 'Доброй ночи';
}

export const ITEM_KIND_LABELS: Record<string, string> = {
  homework: 'Домашнее задание',
  lab: 'Лабораторная',
  control: 'Рубежный контроль',
  test: 'Тест',
  project: 'Проект',
  activity: 'Работа на занятиях',
};

export function itemKindLabel(kind: string): string {
  return ITEM_KIND_LABELS[kind] ?? 'Работа';
}

/** Внутренняя ссылка приложения (защита от javascript:/внешних ссылок в данных). */
export function isInternalLink(link: string | null | undefined): link is string {
  return !!link && link.startsWith('/') && !link.startsWith('//');
}
