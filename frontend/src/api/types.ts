/**
 * Типы ответов API. Источник — реальные ответы сервера в docs/api-examples/*.json
 * и контракты docs/api-contract.md, docs/analytics-contract.md.
 * Даты — строки ISO `YYYY-MM-DD`; дата-время — ISO 8601 (без зоны трактуется как UTC).
 */

export type ISODate = string;
export type ISODateTime = string;

// ---------- Общие ----------

export interface ApiErrorBody {
  detail: string;
  code: string;
  errors?: { field: string; message: string }[];
}

export type Role = 'student' | 'staff';

export interface User {
  id: number;
  login: string;
  role: Role;
  full_name: string;
  display_name: string;
  subtitle: string;
  initials: string;
}

export interface AuthResponse {
  user: User;
  csrf_token: string;
}

export interface Meta {
  app_name: string;
  university_name: string;
  disclaimer: string;
  today: ISODate;
  version: string;
}

export interface FaqItem {
  id: string;
  category: string;
  question: string;
  answer: string;
  link: string | null;
}

export interface FaqResponse {
  items: FaqItem[];
}

// ---------- Профиль ----------

export interface Profile {
  full_name: string;
  last_name: string;
  first_name: string;
  middle_name: string | null;
  university: string;
  faculty: { code: string; name: string };
  program: { code: string; name: string; profile: string | null };
  education_level: string;
  study_form: string;
  funding: string;
  course: number;
  group: string;
  record_book_number: string;
  email: string;
  enrollment_year: number;
  curator: string | null;
  login: string;
}

// ---------- Расписание ----------

export type LessonStatus = 'normal' | 'cancelled' | 'moved_out' | 'moved_in' | 'changed' | 'added';
export type LessonType = 'lecture' | 'seminar' | 'lab' | 'consultation' | string;

export interface TeacherBrief {
  id: number;
  full_name: string;
  position: string | null;
}

export interface LessonChange {
  type: 'cancelled' | 'moved' | 'room' | 'teacher' | 'added' | string;
  title: string;
  text: string;
  reason: string | null;
  old_room?: string | null;
  old_teacher?: TeacherBrief | null;
  new_date?: ISODate | null;
  new_start_time?: string | null;
  original_date?: ISODate | null;
  original_start_time?: string | null;
}

export interface Lesson {
  key: string;
  lesson_id: number | null;
  discipline_id: number | null;
  discipline_title: string;
  discipline_short: string | null;
  lesson_type: LessonType;
  lesson_type_label: string;
  start_time: string;
  end_time: string;
  room: string | null;
  teacher: TeacherBrief | null;
  status: LessonStatus;
  change: LessonChange | null;
}

export type WeekParity = 'odd' | 'even';

export interface ScheduleDay {
  date: ISODate;
  weekday: number;
  weekday_label: string;
  week_number: number;
  week_parity: WeekParity;
  week_parity_label: string;
  is_study_day: boolean;
  changes_count: number;
  lessons: Lesson[];
}

export interface ScheduleResponse {
  today: ISODate;
  group: string;
  period: { title: string; starts_on: ISODate; ends_on: ISODate };
  date_from: ISODate;
  date_to: ISODate;
  days: ScheduleDay[];
}

// ---------- Аналитика ----------

export type AssessmentType = 'credit' | 'distributed_exam' | 'exam';
export type RiskLevel = 'critical' | 'high' | 'medium' | 'low' | 'stable' | 'insufficient_data';
export type IndexZone = 'critical' | 'high' | 'medium' | 'stable';
export type PassStatus = 'secured' | 'achievable' | 'unreachable' | 'passed' | 'failed' | 'unknown';
export type TargetStatus = 'reached' | 'achievable' | 'unreachable' | 'unknown';
export type DataCompleteness = 'full' | 'partial' | 'insufficient';
export type ModuleStatus = 'completed' | 'in_progress' | 'upcoming';
export type ItemState = 'graded' | 'pending' | 'missing';

export interface Risk {
  level: RiskLevel;
  label: string;
  reasons: string[];
  rule?: string;
}

export interface AnalyticsIndex {
  value: number | null;
  max: number;
  zone: IndexZone | null;
  label: string | null;
  is_estimate: boolean;
  formula: string;
  caps_applied: string[];
  uncapped_value?: number | null;
  disciplines_counted?: number;
}

export type ZoneCounts = Record<RiskLevel, number>;

export interface ExamBlock {
  points_min: number;
  points_max: number;
  result: number | null;
  passed: boolean | null;
  required_for_pass: number | null;
  total_at_exam_min: number;
  total_at_exam_max: number;
  final_total?: number | null;
  total_max_possible?: number | null;
}

export interface Target {
  threshold: number;
  grade_key: string;
  label: string;
  status: TargetStatus;
  points_needed_semester: number | null;
  required_share_of_remaining: number | null;
  exam_points_needed: number | null;
  extra_semester_points_needed: number | null;
  reachable_with_current_points?: boolean | null;
  explanation: string;
}

export interface AnalyticsItem {
  id: number;
  title: string;
  kind: string;
  max_points: number;
  points: number | null;
  due_date: ISODate | null;
  state: ItemState;
}

export interface AnalyticsModule {
  id: number;
  ordinal: number;
  title: string;
  status: ModuleStatus;
  ends_on: ISODate | null;
  points: number;
  max_points: number;
  graded_max: number;
  remaining: number;
  missing: number;
  share: number | null;
  is_weak?: boolean;
  topic_ids?: number[];
  items: AnalyticsItem[];
}

export interface NextAction {
  item_id: number;
  title: string;
  kind: string;
  module_id?: number;
  module_title: string;
  max_points: number;
  due_date: ISODate | null;
  days_left: number | null;
  overdue: boolean;
}

export interface DisciplineAnalytics {
  discipline_id: number;
  title: string;
  as_of?: ISODate;
  assessment_type: AssessmentType;
  assessment_type_label: string;
  current_semester_points: number;
  semester_points_max: number;
  completed_points_max: number;
  graded_points_max: number;
  remaining_points_max: number;
  missing_points_max: number;
  max_achievable_semester: number;
  passing_threshold: number;
  semester_target: number;
  semester_points_needed?: number | null;
  semester_progress: number | null;
  data_completeness: DataCompleteness;
  data_issues: string[];
  current_pace: number | null;
  pace_is_reliable: boolean;
  projected_semester_points: number | null;
  required_share_of_remaining: number | null;
  pass_status: PassStatus;
  risk: Risk;
  current_grade: { key: string; label: string } | null;
  exam: ExamBlock | null;
  targets: Target[];
  modules: AnalyticsModule[];
  next_actions: NextAction[];
  weak_topic_ids: number[];
  explanation: string;
  recommendation: string;
}

export interface Priority {
  discipline_id: number;
  title: string;
  risk_level: RiskLevel;
  risk_label: string;
  reason: string;
  action: string;
  points_target: string;
  deadline: ISODate | null;
  score: number;
}

export interface Positive {
  discipline_id: number;
  title: string;
  message: string;
}

export interface AnalyticsSummary {
  as_of?: ISODate;
  index: AnalyticsIndex;
  zone_counts: ZoneCounts;
  explanation: string;
  priorities: Priority[];
  positives: Positive[];
  disciplines: DisciplineAnalytics[];
}

export interface SimulateRequest {
  overrides: { item_id: number; points: number }[];
  exam_points?: number | null;
}

export interface SimulateResponse {
  simulated: boolean;
  analytics: DisciplineAnalytics;
}

// ---------- Дисциплины ----------

export interface Lecturer {
  id: number;
  full_name: string;
  position: string | null;
  department?: string | null;
  email: string | null;
}

export interface DisciplineBrief {
  id: number;
  title: string;
  short_title: string | null;
  department: string | null;
  description: string | null;
  credits: number | null;
  assessment_type: AssessmentType;
  assessment_label: string;
  exam_date: ISODate | null;
  exam_room: string | null;
  lecturer: Lecturer | null;
}

export interface DisciplineTeacher {
  id: number;
  full_name: string;
  position: string | null;
  email: string | null;
  roles: string[];
}

export interface TopicBrief {
  id: number;
  title: string;
  module_id: number | null;
  module_title: string | null;
  module_ordinal: number | null;
  is_weak: boolean;
  resources_count: number;
}

export interface DisciplineDetail {
  discipline: DisciplineBrief;
  teachers: DisciplineTeacher[];
  analytics: DisciplineAnalytics;
  topics: TopicBrief[];
}

// ---------- Темы и материалы ----------

export interface Resource {
  id: number;
  title: string;
  type: string;
  type_label: string;
  source: string | null;
  author: string | null;
  url: string;
  language: string | null;
  summary: string | null;
  relevance: string | null;
  difficulty: string | null;
  duration_minutes: number | null;
  link_status: 'verified' | 'unverified' | string;
  checked_on: ISODate | null;
  access_note: string | null;
}

export interface TopicDetail {
  topic: { id: number; title: string; is_weak: boolean };
  discipline: { id: number; title: string };
  module: { id: number; title: string; ordinal: number } | null;
  resources: Resource[];
}

// ---------- Оценки ----------

export interface Attestation {
  discipline_id: number;
  title: string;
  assessment_type: AssessmentType;
  assessment_label: string;
  exam_date: ISODate | null;
  exam_room: string | null;
}

export interface RecordBookEntry {
  id: number;
  discipline_title: string;
  assessment_type: AssessmentType;
  assessment_label: string;
  points: number | null;
  grade_key: string;
  grade_label: string;
  credits: number | null;
  passed_on: ISODate | null;
}

export interface GradesResponse {
  current: {
    period_title: string;
    session_starts_on: ISODate;
    session_ends_on: ISODate;
    credits_total: number;
    attestations: Attestation[];
  };
  record_book: { semester: number; average: number | null; entries: RecordBookEntry[] }[];
  overall_average: number | null;
}

// ---------- Главная ----------

export interface Deadline {
  item_id: number;
  title: string;
  kind: string;
  max_points: number;
  due_date: ISODate;
  days_left: number;
  discipline_id: number;
  discipline_title: string;
  discipline_short: string | null;
  module_title: string;
}

export interface ApplicationBrief {
  id: number;
  number: string;
  type_key: string;
  title: string;
  status: ApplicationStatus;
  status_label: string;
  updated_at: ISODateTime;
}

export interface Dashboard {
  today: ISODate;
  first_name: string;
  period: {
    title: string;
    week_number: number;
    week_parity: WeekParity;
    week_parity_label: string;
    semester_progress: number;
    ends_on: ISODate;
    session_starts_on: ISODate;
    is_study_day: boolean;
  };
  today_lessons: Lesson[];
  next_lesson: { date: ISODate; weekday_label: string; lesson: Lesson } | null;
  analytics: {
    index: AnalyticsIndex;
    zone_counts: ZoneCounts;
    explanation: string;
    top_priority: Priority | null;
    priorities: {
      discipline_id: number;
      title: string;
      risk_level: RiskLevel;
      risk_label: string | null;
      assessment_type: AssessmentType;
      semester_points_max: number;
      current_semester_points: number;
      remaining_points_max: number;
      missing_points_max: number;
      exam: { result: number | null; points_max: number; points_min: number } | null;
    }[];
  };
  deadlines: Deadline[];
  applications: ApplicationBrief[];
  notifications: { unread_count: number; latest: NotificationItem[] };
}

// ---------- Заявки ----------

export type ApplicationStatus =
  | 'draft'
  | 'submitted'
  | 'in_progress'
  | 'needs_info'
  | 'approved'
  | 'ready'
  | 'completed'
  | 'rejected'
  | 'withdrawn';

export type ApplicationCategory = 'certificate' | 'statement' | 'question';

export type FieldType = 'text' | 'textarea' | 'number' | 'select' | 'date' | 'discipline';

export interface FieldOption {
  value: string | number;
  label: string;
}

export interface FormField {
  name: string;
  label: string;
  type: FieldType;
  required: boolean;
  min_length?: number;
  max_length?: number;
  min?: number;
  max?: number;
  placeholder?: string;
  default?: string | number;
  options?: FieldOption[];
  hint?: string;
}

export interface ApplicationType {
  key: string;
  category: ApplicationCategory;
  title: string;
  description: string;
  processing_days: number;
  icon: string;
  fields: FormField[];
}

export interface ApplicationTypesResponse {
  items: ApplicationType[];
  statuses: Record<ApplicationStatus, string>;
}

export interface ApplicationListItem {
  id: number;
  number: string;
  type_key: string;
  title: string;
  category: ApplicationCategory | null;
  status: ApplicationStatus;
  status_label: string;
  created_at: ISODateTime;
  updated_at: ISODateTime;
  submitted_at: ISODateTime | null;
  summary: string;
  is_active: boolean;
  unread_hint: boolean;
}

export type ApplicationFilter = 'active' | 'draft' | 'closed' | 'all';

export interface ApplicationsResponse {
  items: ApplicationListItem[];
  counts: Record<ApplicationFilter, number>;
}

export interface HistoryEntry {
  id: number;
  from_status: ApplicationStatus | null;
  to_status: ApplicationStatus;
  to_label: string;
  comment: string | null;
  actor_role: Role;
  created_at: ISODateTime;
}

export interface ApplicationMessage {
  id: number;
  author_role: Role;
  author_name: string;
  text: string;
  created_at: ISODateTime;
  is_mine: boolean;
}

export type Payload = Record<string, string | number>;

export interface ApplicationDetail extends ApplicationListItem {
  type: { title: string; description: string; processing_days: number; category: ApplicationCategory };
  payload: Payload;
  payload_display: { name: string; label: string; value: string }[];
  next_step: string;
  history: HistoryEntry[];
  messages: ApplicationMessage[];
  permissions: {
    can_edit: boolean;
    can_submit: boolean;
    can_delete: boolean;
    can_withdraw: boolean;
    can_reply: boolean;
  };
  document_available: boolean;
}

export interface CreateApplicationRequest {
  type_key: string;
  payload: Payload;
  submit: boolean;
}

export interface ElectronicDocument {
  title: string;
  number: string;
  issued_on: ISODate;
  university: string;
  student: {
    full_name: string;
    course: number;
    group: string;
    faculty: string;
    program: string;
    study_form: string;
    funding: string;
    record_book_number: string;
  };
  payload: Payload;
  verification_code: string;
  watermark: string;
}

// ---------- Уведомления ----------

export type NotificationCategory = 'announcement' | 'deadline' | 'schedule' | 'application' | 'grade';

export interface NotificationItem {
  id: number;
  category: NotificationCategory;
  title: string;
  body: string;
  link: string | null;
  importance: 'normal' | 'high';
  created_at: ISODateTime;
  is_read: boolean;
  read_at: ISODateTime | null;
}

export interface NotificationsResponse {
  items: NotificationItem[];
  unread_count: number;
  unread_by_category: Partial<Record<NotificationCategory, number>>;
  categories: Record<NotificationCategory, string>;
}

// ---------- Сотрудник ----------

export interface StudentBrief {
  user_id: number;
  full_name: string;
  group: string;
  course: number;
  faculty: string;
  email: string;
}

export interface StaffApplicationListItem extends ApplicationListItem {
  student: StudentBrief | null;
}

export type StaffApplicationFilter =
  | 'active'
  | 'submitted'
  | 'in_progress'
  | 'needs_info'
  | 'approved'
  | 'ready'
  | 'closed'
  | 'all';

export interface StaffApplicationsResponse {
  items: StaffApplicationListItem[];
  counts: Partial<Record<ApplicationStatus, number>>;
}

export interface StaffTransition {
  status: ApplicationStatus;
  label: string;
  comment_required: boolean;
}

export interface StaffApplicationDetail extends Omit<ApplicationDetail, 'permissions'> {
  student: StudentBrief | null;
  allowed_transitions: StaffTransition[];
  permissions: { can_reply: boolean };
}

export interface StaffStudentsResponse {
  items: StudentBrief[];
}

export interface StaffGradeItem {
  id: number;
  title: string;
  max_points: number;
  due_date: ISODate | null;
  points: number | null;
}

export interface StaffGradeModule {
  id: number;
  ordinal: number;
  title: string;
  status: ModuleStatus;
  items: StaffGradeItem[];
}

export interface StaffGradeDiscipline {
  discipline_id: number;
  title: string;
  assessment_label: string;
  current_points: number;
  semester_points_max: number;
  risk: Risk;
  modules: StaffGradeModule[];
}

export interface StaffStudentGrades {
  student: StudentBrief;
  disciplines: StaffGradeDiscipline[];
}

export interface Announcement {
  id: number;
  title: string;
  body: string;
  audience: string;
  published_at: ISODateTime;
}

export interface AnnouncementRequest {
  title: string;
  body: string;
  audience: string;
  importance: 'normal' | 'high';
}

export interface StaffGroups {
  groups: string[];
  faculties: [string, string][];
}
