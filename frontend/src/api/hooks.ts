import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, qs } from './client';
import type {
  AnalyticsSummary,
  Announcement,
  AnnouncementRequest,
  ApplicationDetail,
  ApplicationFilter,
  ApplicationsResponse,
  ApplicationTypesResponse,
  CreateApplicationRequest,
  Dashboard,
  DisciplineDetail,
  ElectronicDocument,
  FaqResponse,
  GradesResponse,
  Meta,
  NotificationCategory,
  NotificationItem,
  NotificationsResponse,
  Payload,
  Profile,
  ScheduleResponse,
  SimulateRequest,
  SimulateResponse,
  StaffApplicationDetail,
  StaffApplicationFilter,
  StaffApplicationsResponse,
  StaffGroups,
  StaffStructure,
  StaffStudentGrades,
  StaffStudentsResponse,
  TopicDetail,
} from './types';

export const keys = {
  meta: ['meta'] as const,
  faq: ['faq'] as const,
  profile: ['profile'] as const,
  dashboard: ['dashboard'] as const,
  schedule: (from: string, to: string) => ['schedule', from, to] as const,
  analytics: ['analytics'] as const,
  discipline: (id: number) => ['discipline', id] as const,
  topic: (id: number) => ['topic', id] as const,
  grades: ['grades'] as const,
  applicationTypes: ['application-types'] as const,
  applications: (filter: ApplicationFilter) => ['applications', filter] as const,
  applicationsAll: ['applications'] as const,
  application: (id: number) => ['application', id] as const,
  document: (id: number) => ['document', id] as const,
  notifications: (category: NotificationCategory | 'all', unread: boolean) =>
    ['notifications', category, unread] as const,
  notificationsAll: ['notifications'] as const,
  staffApplications: (filter: StaffApplicationFilter) => ['staff', 'applications', filter] as const,
  staffApplicationsAll: ['staff', 'applications'] as const,
  staffApplication: (id: number) => ['staff', 'application', id] as const,
  staffStudents: (group: string) => ['staff', 'students', group] as const,
  staffStructure: ['staff', 'structure'] as const,
  staffGrades: (studentId: number) => ['staff', 'grades', studentId] as const,
  staffAnnouncements: ['staff', 'announcements'] as const,
  staffGroups: ['staff', 'groups'] as const,
};

// ---------- Общие ----------

export function useMeta() {
  return useQuery({
    queryKey: keys.meta,
    queryFn: ({ signal }) => api.get<Meta>('/api/meta', signal),
    staleTime: 10 * 60_000,
  });
}

export function useFaq() {
  return useQuery({
    queryKey: keys.faq,
    queryFn: ({ signal }) => api.get<FaqResponse>('/api/faq', signal),
    staleTime: 10 * 60_000,
  });
}

// ---------- Студент ----------

export function useProfile() {
  return useQuery({ queryKey: keys.profile, queryFn: ({ signal }) => api.get<Profile>('/api/profile', signal) });
}

export function useDashboard() {
  return useQuery({ queryKey: keys.dashboard, queryFn: ({ signal }) => api.get<Dashboard>('/api/dashboard', signal) });
}

export function useSchedule(from: string, to: string, enabled = true) {
  return useQuery({
    queryKey: keys.schedule(from, to),
    queryFn: ({ signal }) => api.get<ScheduleResponse>(`/api/schedule${qs({ from, to })}`, signal),
    enabled,
    placeholderData: (prev) => prev,
  });
}

export function useAnalytics() {
  return useQuery({
    queryKey: keys.analytics,
    queryFn: ({ signal }) => api.get<AnalyticsSummary>('/api/analytics', signal),
  });
}

export function useDiscipline(id: number) {
  return useQuery({
    queryKey: keys.discipline(id),
    queryFn: ({ signal }) => api.get<DisciplineDetail>(`/api/disciplines/${id}`, signal),
    enabled: Number.isFinite(id),
  });
}

export function useSimulate(id: number) {
  return useMutation({
    mutationFn: (body: SimulateRequest) => api.post<SimulateResponse>(`/api/disciplines/${id}/simulate`, body),
  });
}

export function useTopic(id: number) {
  return useQuery({
    queryKey: keys.topic(id),
    queryFn: ({ signal }) => api.get<TopicDetail>(`/api/topics/${id}`, signal),
    enabled: Number.isFinite(id),
  });
}

export function useGrades(enabled = true) {
  return useQuery({
    queryKey: keys.grades,
    queryFn: ({ signal }) => api.get<GradesResponse>('/api/grades', signal),
    enabled,
  });
}

// ---------- Заявки ----------

export function useApplicationTypes() {
  return useQuery({
    queryKey: keys.applicationTypes,
    queryFn: ({ signal }) => api.get<ApplicationTypesResponse>('/api/application-types', signal),
    staleTime: 5 * 60_000,
  });
}

export function useApplications(filter: ApplicationFilter) {
  return useQuery({
    queryKey: keys.applications(filter),
    queryFn: ({ signal }) => api.get<ApplicationsResponse>(`/api/applications${qs({ status: filter })}`, signal),
    placeholderData: (prev) => prev,
  });
}

export function useApplication(id: number) {
  return useQuery({
    queryKey: keys.application(id),
    queryFn: ({ signal }) => api.get<ApplicationDetail>(`/api/applications/${id}`, signal),
    enabled: Number.isFinite(id),
  });
}

export function useApplicationDocument(id: number) {
  return useQuery({
    queryKey: keys.document(id),
    queryFn: ({ signal }) => api.get<ElectronicDocument>(`/api/applications/${id}/document`, signal),
    enabled: Number.isFinite(id),
    retry: false,
  });
}

/** Общая инвалидация после изменения заявки студентом. */
function useApplicationInvalidation() {
  const qc = useQueryClient();
  return (detail?: ApplicationDetail) => {
    if (detail) qc.setQueryData(keys.application(detail.id), detail);
    void qc.invalidateQueries({ queryKey: keys.applicationsAll });
    void qc.invalidateQueries({ queryKey: keys.dashboard });
  };
}

export function useCreateApplication() {
  const after = useApplicationInvalidation();
  return useMutation({
    mutationFn: (body: CreateApplicationRequest) => api.post<ApplicationDetail>('/api/applications', body),
    onSuccess: (data) => after(data),
  });
}

export function useUpdateDraft(id: number) {
  const after = useApplicationInvalidation();
  return useMutation({
    mutationFn: (payload: Payload) => api.patch<ApplicationDetail>(`/api/applications/${id}`, { payload }),
    onSuccess: (data) => after(data),
  });
}

export function useApplicationAction(id: number) {
  const after = useApplicationInvalidation();
  return useMutation({
    mutationFn: (action: 'submit' | 'withdraw') => api.post<ApplicationDetail>(`/api/applications/${id}/${action}`),
    onSuccess: (data) => after(data),
  });
}

export function useDeleteDraft(id: number) {
  const qc = useQueryClient();
  const after = useApplicationInvalidation();
  return useMutation({
    mutationFn: () => api.del<null>(`/api/applications/${id}`),
    onSuccess: () => {
      qc.removeQueries({ queryKey: keys.application(id) });
      after();
    },
  });
}

export function useSendMessage(id: number) {
  const after = useApplicationInvalidation();
  return useMutation({
    mutationFn: (text: string) => api.post<ApplicationDetail>(`/api/applications/${id}/messages`, { text }),
    onSuccess: (data) => after(data),
  });
}

// ---------- Уведомления ----------

export function useNotifications(category: NotificationCategory | 'all' = 'all', unread = false, enabled = true) {
  return useQuery({
    queryKey: keys.notifications(category, unread),
    queryFn: ({ signal }) =>
      api.get<NotificationsResponse>(
        `/api/notifications${qs({ category: category === 'all' ? undefined : category, unread: unread || undefined })}`,
        signal,
      ),
    enabled,
    placeholderData: (prev) => prev,
  });
}

/** Счётчик непрочитанных для навигации (общий кэш со списком «Все»). */
export function useUnreadCount(enabled: boolean): number {
  const q = useQuery({
    queryKey: keys.notifications('all', false),
    queryFn: ({ signal }) => api.get<NotificationsResponse>('/api/notifications', signal),
    enabled,
    refetchInterval: 60_000,
  });
  return q.data?.unread_count ?? 0;
}

export function useMarkRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.post<NotificationItem>(`/api/notifications/${id}/read`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: keys.notificationsAll });
      void qc.invalidateQueries({ queryKey: keys.dashboard });
    },
  });
}

export function useMarkAllRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (category: NotificationCategory | 'all') =>
      api.post<{ updated: number }>('/api/notifications/read-all', { category }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: keys.notificationsAll });
      void qc.invalidateQueries({ queryKey: keys.dashboard });
    },
  });
}

// ---------- Сотрудник ----------

export function useStaffApplications(filter: StaffApplicationFilter) {
  return useQuery({
    queryKey: keys.staffApplications(filter),
    queryFn: ({ signal }) =>
      api.get<StaffApplicationsResponse>(`/api/staff/applications${qs({ status: filter })}`, signal),
    placeholderData: (prev) => prev,
  });
}

export function useStaffApplication(id: number) {
  return useQuery({
    queryKey: keys.staffApplication(id),
    queryFn: ({ signal }) => api.get<StaffApplicationDetail>(`/api/staff/applications/${id}`, signal),
    enabled: Number.isFinite(id),
  });
}

function useStaffAppUpdate(id: number) {
  const qc = useQueryClient();
  return (data: StaffApplicationDetail) => {
    qc.setQueryData(keys.staffApplication(id), data);
    void qc.invalidateQueries({ queryKey: keys.staffApplicationsAll });
  };
}

export function useStaffChangeStatus(id: number) {
  const after = useStaffAppUpdate(id);
  return useMutation({
    mutationFn: (body: { to_status: string; comment: string | null }) =>
      api.post<StaffApplicationDetail>(`/api/staff/applications/${id}/status`, body),
    onSuccess: after,
  });
}

export function useStaffSendMessage(id: number) {
  const after = useStaffAppUpdate(id);
  return useMutation({
    mutationFn: (text: string) => api.post<StaffApplicationDetail>(`/api/staff/applications/${id}/messages`, { text }),
    onSuccess: after,
  });
}

export function useStaffStructure() {
  return useQuery({
    queryKey: keys.staffStructure,
    queryFn: ({ signal }) => api.get<StaffStructure>('/api/staff/structure', signal),
    staleTime: 5 * 60_000,
  });
}

export function useStaffStudents(group: string | null) {
  return useQuery({
    queryKey: keys.staffStudents(group ?? ''),
    queryFn: ({ signal }) => api.get<StaffStudentsResponse>(`/api/staff/students${qs({ group: group ?? undefined })}`, signal),
    enabled: !!group,
    staleTime: 60_000,
  });
}

export function useStaffStudentGrades(studentId: number | null) {
  return useQuery({
    queryKey: keys.staffGrades(studentId ?? -1),
    queryFn: ({ signal }) => api.get<StaffStudentGrades>(`/api/staff/students/${studentId}/grades`, signal),
    enabled: studentId !== null && Number.isFinite(studentId),
  });
}

export function useStaffAnnouncements() {
  return useQuery({
    queryKey: keys.staffAnnouncements,
    queryFn: ({ signal }) => api.get<{ items: Announcement[] }>('/api/staff/announcements', signal),
  });
}

export function useStaffGroups() {
  return useQuery({
    queryKey: keys.staffGroups,
    queryFn: ({ signal }) => api.get<StaffGroups>('/api/staff/groups', signal),
    staleTime: 10 * 60_000,
  });
}

export function usePublishAnnouncement() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AnnouncementRequest) =>
      api.post<{ id: number; recipients: number }>('/api/staff/announcements', body),
    onSuccess: () => void qc.invalidateQueries({ queryKey: keys.staffAnnouncements }),
  });
}
