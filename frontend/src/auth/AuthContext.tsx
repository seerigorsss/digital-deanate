import { createContext, useCallback, useContext, useEffect, useMemo, type ReactNode } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { ApiError, request, setCsrfToken, setUnauthorizedHandler } from '../api/client';
import type { AuthResponse, User } from '../api/types';

const ME_KEY = ['me'] as const;

interface AuthContextValue {
  user: User | null;
  status: 'loading' | 'authenticated' | 'anonymous' | 'error';
  error: unknown;
  retry: () => void;
  login: (login: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

async function fetchMe(): Promise<User | null> {
  try {
    const data = await request<AuthResponse>('GET', '/api/auth/me', { skipAuthRedirect: true });
    setCsrfToken(data.csrf_token);
    return data.user;
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) {
      setCsrfToken(null);
      return null;
    }
    throw e;
  }
}

export function homePathFor(user: User | null): string {
  return user?.role === 'staff' ? '/staff' : '/';
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const me = useQuery({ queryKey: ME_KEY, queryFn: fetchMe, staleTime: Infinity, retry: 1 });

  const dropUserData = useCallback(() => {
    qc.removeQueries({ predicate: (q) => q.queryKey[0] !== 'me' && q.queryKey[0] !== 'meta' && q.queryKey[0] !== 'faq' });
  }, [qc]);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      // Сессия истекла: показываем вход и возвращаем пользователя туда, где он был.
      setCsrfToken(null);
      qc.setQueryData(ME_KEY, null);
      dropUserData();
      const here = window.location.pathname + window.location.search;
      if (!window.location.pathname.startsWith('/login')) {
        navigate(`/login?next=${encodeURIComponent(here)}&expired=1`, { replace: true });
      }
    });
    return () => setUnauthorizedHandler(null);
  }, [qc, navigate, dropUserData]);

  const login = useCallback(
    async (loginValue: string, password: string) => {
      const data = await request<AuthResponse>('POST', '/api/auth/login', {
        body: { login: loginValue, password },
        skipAuthRedirect: true,
      });
      setCsrfToken(data.csrf_token);
      dropUserData();
      qc.setQueryData(ME_KEY, data.user);
      return data.user;
    },
    [qc, dropUserData],
  );

  const logout = useCallback(async () => {
    try {
      await request<null>('POST', '/api/auth/logout', { body: {}, skipAuthRedirect: true });
    } catch {
      // Даже если сервер недоступен, локально выходим: cookie HttpOnly истечёт на сервере.
    }
    setCsrfToken(null);
    qc.setQueryData(ME_KEY, null);
    dropUserData();
    navigate('/login', { replace: true });
  }, [qc, navigate, dropUserData]);

  const value = useMemo<AuthContextValue>(() => {
    let status: AuthContextValue['status'];
    if (me.isPending) status = 'loading';
    else if (me.isError && me.data === undefined) status = 'error';
    else status = me.data ? 'authenticated' : 'anonymous';
    return {
      user: me.data ?? null,
      status,
      error: me.error,
      retry: () => void me.refetch(),
      login,
      logout,
    };
  }, [me.data, me.isPending, me.isError, me.error, me.refetch, login, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
