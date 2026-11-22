import { lazy, Suspense, type ReactNode } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import type { Role } from './api/types';
import { homePathFor, useAuth } from './auth/AuthContext';
import { AppShell } from './components/layout/AppShell';
import { ErrorState, PageSkeleton } from './components/ui/States';
import { ErrorBoundary } from './components/layout/ErrorBoundary';
import { LoginPage } from './pages/LoginPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { HomePage } from './pages/HomePage';

const SchedulePage = lazy(() => import('./pages/SchedulePage'));
const StudyPage = lazy(() => import('./pages/StudyPage'));
const DisciplinePage = lazy(() => import('./pages/DisciplinePage'));
const TopicPage = lazy(() => import('./pages/TopicPage'));
const ApplicationsPage = lazy(() => import('./pages/ApplicationsPage'));
const NewApplicationPage = lazy(() => import('./pages/NewApplicationPage'));
const ApplicationPage = lazy(() => import('./pages/ApplicationPage'));
const DocumentPage = lazy(() => import('./pages/DocumentPage'));
const NotificationsPage = lazy(() => import('./pages/NotificationsPage'));
const ProfilePage = lazy(() => import('./pages/ProfilePage'));
const HelpPage = lazy(() => import('./pages/HelpPage'));
const StaffQueuePage = lazy(() => import('./pages/staff/StaffQueuePage'));
const StaffApplicationPage = lazy(() => import('./pages/staff/StaffApplicationPage'));
const StaffGradesPage = lazy(() => import('./pages/staff/StaffGradesPage'));
const StaffAnnouncementsPage = lazy(() => import('./pages/staff/StaffAnnouncementsPage'));

function FullScreenStatus() {
  const { status, error, retry } = useAuth();
  if (status === 'error') {
    return (
      <div className="auth-page">
        <div className="auth-wrap">
          <div className="card auth-card">
            <ErrorState error={error} onRetry={retry} title="Не удалось связаться с сервером" />
          </div>
        </div>
      </div>
    );
  }
  return (
    <div className="auth-page" aria-busy="true">
      <span className="sr-only" role="status">
        Загрузка…
      </span>
    </div>
  );
}

/** Защита маршрута: гость → /login?next=…, чужая роль → свой раздел. */
function Guard({ role, children }: { role: Role; children: ReactNode }) {
  const { user, status } = useAuth();
  const location = useLocation();
  if (status === 'loading' || status === 'error') return <FullScreenStatus />;
  if (!user) {
    const next = location.pathname + location.search;
    return <Navigate to={`/login?next=${encodeURIComponent(next)}`} replace />;
  }
  if (user.role !== role) return <Navigate to={homePathFor(user)} replace />;
  return (
    <AppShell>
      <ErrorBoundary key={location.pathname}>
        <Suspense fallback={<PageSkeleton />}>{children}</Suspense>
      </ErrorBoundary>
    </AppShell>
  );
}

function CatchAll() {
  const { user, status } = useAuth();
  if (status === 'loading') return <FullScreenStatus />;
  if (user) {
    return (
      <AppShell>
        <NotFoundPage />
      </AppShell>
    );
  }
  return <NotFoundPage standalone />;
}

const S = (el: ReactNode) => <Guard role="student">{el}</Guard>;
const T = (el: ReactNode) => <Guard role="staff">{el}</Guard>;

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={S(<HomePage />)} />
      <Route path="/schedule" element={S(<SchedulePage />)} />
      <Route path="/study" element={S(<StudyPage />)} />
      <Route path="/study/:disciplineId" element={S(<DisciplinePage />)} />
      <Route path="/study/:disciplineId/topics/:topicId" element={S(<TopicPage />)} />
      <Route path="/applications" element={S(<ApplicationsPage />)} />
      <Route path="/applications/new" element={S(<NewApplicationPage />)} />
      <Route path="/applications/:id" element={S(<ApplicationPage />)} />
      <Route path="/applications/:id/document" element={S(<DocumentPage />)} />
      <Route path="/notifications" element={S(<NotificationsPage />)} />
      <Route path="/profile" element={S(<ProfilePage />)} />
      <Route path="/help" element={S(<HelpPage />)} />
      <Route path="/staff" element={T(<StaffQueuePage />)} />
      <Route path="/staff/applications" element={<Navigate to="/staff" replace />} />
      <Route path="/staff/applications/:id" element={T(<StaffApplicationPage />)} />
      <Route path="/staff/grades" element={T(<StaffGradesPage />)} />
      <Route path="/staff/announcements" element={T(<StaffAnnouncementsPage />)} />
      <Route path="*" element={<CatchAll />} />
    </Routes>
  );
}
