import type { ApiErrorBody, AuthResponse } from './types';

/**
 * Fetch-клиент API.
 * - cookie сессии HttpOnly, браузер отправляет её сам (credentials: 'same-origin');
 * - CSRF-токен хранится только в памяти и добавляется ко всем не-GET запросам;
 * - единый формат ошибок {detail, code, errors};
 * - 401 → обработчик onUnauthorized (переход на /login?next=…);
 * - 403 csrf_failed → один раз перезапрашиваем /api/auth/me и повторяем запрос.
 */

let csrfToken: string | null = null;
let unauthorizedHandler: (() => void) | null = null;

export function setCsrfToken(token: string | null): void {
  csrfToken = token;
}

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  unauthorizedHandler = handler;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly errors: { field: string; message: string }[];

  constructor(status: number, body: Partial<ApiErrorBody>) {
    super(body.detail || 'Не удалось выполнить запрос');
    this.name = 'ApiError';
    this.status = status;
    this.code = body.code || `http_${status}`;
    this.errors = body.errors ?? [];
  }

  /** Ошибки по полям: { имя_поля: сообщение } */
  get fieldErrors(): Record<string, string> {
    const out: Record<string, string> = {};
    for (const e of this.errors) {
      if (e.field && !out[e.field]) out[e.field] = e.message;
    }
    return out;
  }

  get isNetwork(): boolean {
    return this.status === 0;
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }
}

type Method = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

interface RequestOptions {
  body?: unknown;
  signal?: AbortSignal;
  /** Не вызывать глобальный обработчик 401 (для /auth/me и /auth/login). */
  skipAuthRedirect?: boolean;
}

const AUTH_PATHS = ['/api/auth/login', '/api/auth/me'];

async function refreshCsrf(): Promise<boolean> {
  try {
    const res = await fetch('/api/auth/me', { credentials: 'same-origin', headers: { Accept: 'application/json' } });
    if (!res.ok) return false;
    const data = (await res.json()) as AuthResponse;
    csrfToken = data.csrf_token;
    return true;
  } catch {
    return false;
  }
}

async function doFetch(method: Method, path: string, opts: RequestOptions): Promise<Response> {
  const headers: Record<string, string> = { Accept: 'application/json' };
  let body: string | undefined;
  if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(opts.body);
  }
  if (method !== 'GET' && csrfToken) headers['X-CSRF-Token'] = csrfToken;
  return fetch(path, { method, headers, body, credentials: 'same-origin', signal: opts.signal });
}

export async function request<T>(method: Method, path: string, opts: RequestOptions = {}): Promise<T> {
  let res: Response;
  try {
    if (method !== 'GET' && !csrfToken && !AUTH_PATHS.includes(path)) await refreshCsrf();
    res = await doFetch(method, path, opts);
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') throw e;
    throw new ApiError(0, {
      detail: 'Нет соединения с сервером. Проверьте интернет и попробуйте ещё раз.',
      code: 'network_error',
    });
  }

  let data: unknown = null;
  if (res.status !== 204) {
    const text = await res.text();
    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = null;
      }
    }
  }

  if (res.ok) return data as T;

  const errBody = (data && typeof data === 'object' ? data : {}) as Partial<ApiErrorBody>;

  if (res.status === 403 && errBody.code === 'csrf_failed' && method !== 'GET') {
    // Токен устарел (например, после повторного входа в другой вкладке) — обновляем и повторяем один раз.
    if (await refreshCsrf()) {
      try {
        const retry = await doFetch(method, path, opts);
        if (retry.ok) {
          const t = retry.status === 204 ? '' : await retry.text();
          return (t ? JSON.parse(t) : null) as T;
        }
        const retryText = await retry.text();
        let retryBody: Partial<ApiErrorBody> = {};
        try {
          retryBody = retryText ? (JSON.parse(retryText) as Partial<ApiErrorBody>) : {};
        } catch {
          retryBody = {};
        }
        if (retry.status === 401 && !opts.skipAuthRedirect) unauthorizedHandler?.();
        throw new ApiError(retry.status, retryBody);
      } catch (e) {
        if (e instanceof ApiError) throw e;
        throw new ApiError(0, { detail: 'Нет соединения с сервером.', code: 'network_error' });
      }
    }
  }

  if (res.status === 401 && !opts.skipAuthRedirect && !AUTH_PATHS.includes(path)) {
    unauthorizedHandler?.();
  }

  if (res.status >= 500 && !errBody.detail) {
    errBody.detail = 'Сервер временно недоступен. Попробуйте ещё раз через минуту.';
  }
  throw new ApiError(res.status, errBody);
}

export const api = {
  get: <T>(path: string, signal?: AbortSignal) => request<T>('GET', path, { signal }),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, { body: body ?? {} }),
  put: <T>(path: string, body?: unknown) => request<T>('PUT', path, { body }),
  patch: <T>(path: string, body?: unknown) => request<T>('PATCH', path, { body }),
  del: <T>(path: string) => request<T>('DELETE', path),
};

/** Сообщение для пользователя по любой ошибке. */
export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error && err.message) return 'Что-то пошло не так. Попробуйте ещё раз.';
  return 'Что-то пошло не так. Попробуйте ещё раз.';
}

export function qs(params: Record<string, string | number | boolean | null | undefined>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === '') continue;
    sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : '';
}
