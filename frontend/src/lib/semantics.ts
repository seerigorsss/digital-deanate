import {
  AlarmClock,
  BookOpen,
  CalendarClock,
  ChartColumn,
  Check,
  CheckCheck,
  CircleAlert,
  CircleCheck,
  CircleCheckBig,
  CircleDashed,
  CircleX,
  ClipboardCheck,
  Clock,
  FileCheck,
  FileText,
  FlaskConical,
  GraduationCap,
  HandHeart,
  Hourglass,
  List,
  type LucideIcon,
  Megaphone,
  MessageCircle,
  MessageCircleQuestion,
  OctagonAlert,
  PackageCheck,
  PencilLine,
  Presentation,
  Send,
  Shield,
  ShieldCheck,
  TriangleAlert,
  Undo2,
  Video,
  Wallet,
  X,
} from 'lucide-react';
import type { ApplicationStatus, IndexZone, ModuleStatus, NotificationCategory, RiskLevel, TargetStatus } from '../api/types';

/** Семантика зон риска: цвет (класс tone-*) всегда вместе с иконкой и текстом. */
export interface ToneMeta {
  tone: string;
  icon: LucideIcon;
  label: string;
}

export const RISK_META: Record<RiskLevel, ToneMeta> = {
  critical: { tone: 'critical', icon: OctagonAlert, label: 'Критический риск' },
  high: { tone: 'high', icon: TriangleAlert, label: 'Высокий риск' },
  medium: { tone: 'medium', icon: CircleAlert, label: 'Средний риск' },
  low: { tone: 'low', icon: CircleCheck, label: 'Низкий риск' },
  stable: { tone: 'stable', icon: ShieldCheck, label: 'Стабильно' },
  insufficient_data: { tone: 'nodata', icon: Hourglass, label: 'Недостаточно данных' },
};

export const RISK_ORDER: RiskLevel[] = ['critical', 'high', 'medium', 'low', 'stable', 'insufficient_data'];

export const ZONE_META: Record<IndexZone, ToneMeta> = {
  critical: { tone: 'critical', icon: OctagonAlert, label: 'Критично' },
  high: { tone: 'high', icon: TriangleAlert, label: 'Высокий риск' },
  medium: { tone: 'medium', icon: CircleAlert, label: 'Требует внимания' },
  stable: { tone: 'stable', icon: ShieldCheck, label: 'Стабильно' },
};

export const TARGET_META: Record<TargetStatus, ToneMeta> = {
  reached: { tone: 'stable', icon: CheckCheck, label: 'Достигнуто' },
  achievable: { tone: 'info', icon: Check, label: 'Достижимо' },
  unreachable: { tone: 'muted', icon: X, label: 'Недостижимо' },
  unknown: { tone: 'nodata', icon: CircleDashed, label: 'Нет данных' },
};

export const MODULE_STATUS_LABEL: Record<ModuleStatus, string> = {
  completed: 'Завершён',
  in_progress: 'Идёт сейчас',
  upcoming: 'Впереди',
};

export const STATUS_META: Record<ApplicationStatus, ToneMeta> = {
  draft: { tone: 'neutral', icon: PencilLine, label: 'Черновик' },
  submitted: { tone: 'info', icon: Send, label: 'Отправлена' },
  in_progress: { tone: 'info', icon: Clock, label: 'В обработке' },
  needs_info: { tone: 'attention', icon: MessageCircleQuestion, label: 'Требуется уточнение' },
  approved: { tone: 'success', icon: Check, label: 'Одобрена' },
  ready: { tone: 'success-strong', icon: PackageCheck, label: 'Готова к получению' },
  completed: { tone: 'dark', icon: CircleCheckBig, label: 'Завершена' },
  rejected: { tone: 'danger', icon: CircleX, label: 'Отклонена' },
  withdrawn: { tone: 'withdrawn', icon: Undo2, label: 'Отозвана' },
};

export const NOTIFICATION_META: Record<NotificationCategory, { icon: LucideIcon; label: string }> = {
  announcement: { icon: Megaphone, label: 'Объявления' },
  deadline: { icon: AlarmClock, label: 'Сроки' },
  schedule: { icon: CalendarClock, label: 'Расписание' },
  application: { icon: FileText, label: 'Заявки' },
  grade: { icon: ChartColumn, label: 'Баллы' },
};

export const NOTIFICATION_CATEGORIES: NotificationCategory[] = ['announcement', 'deadline', 'schedule', 'application', 'grade'];

const TYPE_ICONS: Record<string, LucideIcon> = {
  'file-check': FileCheck,
  wallet: Wallet,
  shield: Shield,
  list: List,
  'calendar-clock': CalendarClock,
  'hand-heart': HandHeart,
  'message-circle': MessageCircle,
};

export function applicationTypeIcon(icon: string | undefined): LucideIcon {
  return (icon && TYPE_ICONS[icon]) || FileText;
}

const RESOURCE_ICONS: Record<string, LucideIcon> = {
  video: Video,
  lecture: Presentation,
  textbook: BookOpen,
  course: GraduationCap,
  practice: FlaskConical,
  notes: ClipboardCheck,
};

export function resourceIcon(type: string): LucideIcon {
  return RESOURCE_ICONS[type] ?? BookOpen;
}

export const CATEGORY_LABELS: Record<string, string> = {
  certificate: 'Справки',
  statement: 'Заявления',
  question: 'Обращения',
};

