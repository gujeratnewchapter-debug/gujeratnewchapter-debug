import axios, { AxiosHeaders } from 'axios';
import type { AxiosResponse } from 'axios';
import { supabase } from './supabase';
import { getStoredDjangoAccessToken, isCompactJwtToken, isUsableJwtToken } from './auth-token';
import { assertValidHttpHeaderValue, normalizePublicEnvironmentValue } from './http-headers';

const DEFAULT_API_BASE_URL =
  process.env.NODE_ENV === 'development'
    ? 'http://localhost:8000/api'
    : 'https://ethiopian-startup-school-api.onrender.com/api';
const PUBLIC_CONTENT_TIMEOUT = 65_000;
const AUTH_REQUEST_TIMEOUT = 65_000;

export const API_BASE_URL =
  normalizePublicEnvironmentValue(process.env.NEXT_PUBLIC_API_BASE_URL, 'NEXT_PUBLIC_API_BASE_URL')
  || DEFAULT_API_BASE_URL;
const COURSE_DETAIL_CACHE_MS = 15_000;
const courseDetailRequests = new Map<string, { expiresAt: number; promise: Promise<any> }>();
const sessionExchangeRequests = new Map<string, Promise<any>>();

export const apiClient = axios.create({ baseURL: API_BASE_URL, timeout: 15000 });
let sessionSyncPromise: Promise<any> | null = null;

function createBearerAuthorization(token: string) {
  if (!isCompactJwtToken(token)) {
    throw new Error('Refusing to send a malformed authentication token');
  }
  return `Bearer ${token}`;
}

function validateRequestHeaders(headers: AxiosHeaders) {
  for (const [name, value] of Object.entries(headers.toJSON(true))) {
    if (value == null) continue;
    assertValidHttpHeaderValue(name, String(value));
  }
}

export function resolveMediaUrl(image?: string | null) {
  if (!image) return null;
  if (/^https?:\/\//i.test(image) || image.startsWith('data:') || image.startsWith('blob:')) return image;
  const origin = API_BASE_URL.replace(/\/api\/?$/, '');
  return new URL(image, `${origin}/`).toString();
}

function clearCourseDetailRequests() {
  courseDetailRequests.clear();
}

apiClient.interceptors.request.use(async (config) => {
  const djangoToken = getStoredDjangoAccessToken();
  const headers = config.headers ?? {};

  if (!(headers as Record<string, string>).Authorization) {
    if (djangoToken && isUsableJwtToken(djangoToken)) {
      (headers as Record<string, string>).Authorization = createBearerAuthorization(djangoToken);
    } else {
      delete (headers as Record<string, string>).Authorization;
    }
  }

  const normalizedHeaders = AxiosHeaders.from(headers);
  const authorization = normalizedHeaders.get('Authorization');
  if (authorization != null
    && (typeof authorization !== 'string'
      || !/^Bearer [A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/.test(authorization))) {
    throw new Error('Refusing to send a malformed Authorization header');
  }

  config.headers = normalizedHeaders;
  validateRequestHeaders(normalizedHeaders);
  return config;
});

apiClient.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    const status = error.response?.status;
    const requestPath = original?.url?.split('?')[0].replace(/\/+$/, '');
    const isSessionSyncRequest = requestPath?.endsWith('/auth/session/sync');
    const retryConfig = original as (typeof original & { _transientRetryCount?: number }) | undefined;
    const isTransientFailure =
      !error.response
      || status === 502
      || status === 503
      || status === 504;

    if (
      retryConfig
      && retryConfig.method?.toLowerCase() === 'get'
      && !isSessionSyncRequest
      && isTransientFailure
      && (retryConfig._transientRetryCount ?? 0) < 2
    ) {
      const retryCount = retryConfig._transientRetryCount ?? 0;
      retryConfig._transientRetryCount = retryCount + 1;
      await new Promise((resolve) => setTimeout(resolve, retryCount === 0 ? 1000 : 3000));
      return apiClient(retryConfig);
    }

    if (status === 401 && original && !original._authRetry && !isSessionSyncRequest) {
      original._authRetry = true;
      try {
        const { data: sessionData } = await syncSupabaseSessionFromBrowser();
        setDjangoAuthToken(sessionData.access);
        original.headers = original.headers ?? {};
        original.headers.Authorization = createBearerAuthorization(sessionData.access);
        return apiClient(original);
      } catch {
        clearDjangoAuthToken();
      }
    }

    return Promise.reject(error);
  }
);

async function syncSupabaseSessionFromBrowser() {
  if (!sessionSyncPromise) {
    sessionSyncPromise = (async () => {
      const { data: { session }, error } = await supabase.auth.getSession();
      if (error || !session?.access_token) {
        throw error || new Error('No active Supabase session');
      }
      return syncSupabaseSession(session.access_token);
    })();
  }

  const pendingSync = sessionSyncPromise;
  try {
    return await pendingSync;
  } finally {
    if (sessionSyncPromise === pendingSync) sessionSyncPromise = null;
  }
}

// ---- Auth ----
export const register = (payload: {
  username?: string; email: string; password: string;
  first_name?: string; last_name?: string; full_name?: string;
  role: 'student' | 'instructor';
}) => apiClient.post('/auth/register/', payload, { timeout: AUTH_REQUEST_TIMEOUT });

export const login = (username: string, password: string) =>
  apiClient.post('/auth/login/', { username, password }, { timeout: AUTH_REQUEST_TIMEOUT });

export const syncSupabaseSession = (accessToken: string) =>
  apiClient.get('/auth/session/sync/', {
    headers: { Authorization: createBearerAuthorization(accessToken) },
    timeout: AUTH_REQUEST_TIMEOUT,
  });

export function syncSupabaseSessionWithRefresh(accessToken: string) {
  const pending = sessionExchangeRequests.get(accessToken);
  if (pending) return pending;

  const request = (async () => {
    try {
      return await syncSupabaseSession(accessToken);
    } catch (syncError: any) {
      const status = syncError?.response?.status;
      if (status !== 401 && status !== 403) throw syncError;

      const { data, error } = await supabase.auth.refreshSession();
      const refreshedToken = data.session?.access_token;
      if (error || !refreshedToken) throw syncError;
      return syncSupabaseSession(refreshedToken);
    }
  })();

  sessionExchangeRequests.set(accessToken, request);
  void request.finally(() => {
    if (sessionExchangeRequests.get(accessToken) === request) {
      sessionExchangeRequests.delete(accessToken);
    }
  }).catch(() => undefined);
  return request;
}

export const googleLogin = (id_token: string, role: 'student' | 'instructor' = 'student') =>
  apiClient.post('/auth/login/google/', { id_token, role }, { timeout: AUTH_REQUEST_TIMEOUT });

export function setDjangoAuthToken(accessToken: string | null) {
  clearCourseDetailRequests();
  if (accessToken) {
    try {
      localStorage.setItem('django_access', accessToken);
    } catch (e) {
      /* ignore */
    }
  } else {
    try { localStorage.removeItem('django_access'); } catch (e) { /* ignore */ }
  }
}

export function clearDjangoAuthToken() {
  clearCourseDetailRequests();
  try { localStorage.removeItem('django_access'); localStorage.removeItem('django_refresh'); } catch (e) { /* ignore */ }
}

export const verifyEmail = (token: string) => apiClient.post('/auth/verify-email/', { token });
export const resendVerification = () => apiClient.post('/auth/resend-verification/');
export const getMe = () => apiClient.get('/auth/me/', { timeout: AUTH_REQUEST_TIMEOUT });
export const updateMe = (payload: any) => apiClient.patch('/auth/me/', payload);

// ---- Site settings ----
export const getSiteSettings = () => apiClient.get('/site-settings/', { timeout: PUBLIC_CONTENT_TIMEOUT, params: { _fresh: Date.now() } });
export const getPageContent = (slug: string) => apiClient.get(`/page-content/${slug}/`, { timeout: PUBLIC_CONTENT_TIMEOUT, params: { _fresh: Date.now() } });

// ---- News ----
export type NewsArticle = {
  id: number;
  title: string;
  slug: string;
  short_description: string;
  content: string;
  featured_image: string | null;
  image_alt_text: string;
  category: string;
  author: string;
  published_at: string | null;
  is_published: boolean;
  is_featured: boolean;
  created_at: string;
  updated_at: string;
};

export const getNews = (): Promise<AxiosResponse<NewsArticle[]>> =>
  apiClient.get('/news/', { timeout: PUBLIC_CONTENT_TIMEOUT, params: { _fresh: Date.now() } });
export const getFeaturedNews = (): Promise<AxiosResponse<NewsArticle[]>> =>
  apiClient.get('/news/', {
    timeout: PUBLIC_CONTENT_TIMEOUT,
    params: { featured: 'true', _fresh: Date.now() },
  });
export const getNewsArticle = (slug: string) =>
  apiClient.get(`/news/${encodeURIComponent(slug)}/`, { timeout: PUBLIC_CONTENT_TIMEOUT });
export const createNewsArticle = (payload: FormData) =>
  apiClient.post('/news/', payload, { timeout: AUTH_REQUEST_TIMEOUT });
export const updateNewsArticle = (slug: string, payload: FormData) =>
  apiClient.patch(`/news/${encodeURIComponent(slug)}/`, payload, { timeout: AUTH_REQUEST_TIMEOUT });
export const deleteNewsArticle = (slug: string) =>
  apiClient.delete(`/news/${encodeURIComponent(slug)}/`, { timeout: AUTH_REQUEST_TIMEOUT });

// ---- Courses ----
export const getCourses = (params?: Record<string, any>) => apiClient.get('/courses/', { timeout: PUBLIC_CONTENT_TIMEOUT, params: { ...params, _fresh: Date.now() } });
export function getCourse(id: number | string, forceRefresh = false) {
  const key = String(id);
  const cached = courseDetailRequests.get(key);
  if (!forceRefresh && cached && cached.expiresAt > Date.now()) return cached.promise;

  const request = () => apiClient.get(`/courses/${id}/`, {
    timeout: PUBLIC_CONTENT_TIMEOUT,
    params: { _fresh: Date.now() },
  });
  const promise = request()
    .catch(async (error) => {
      if (!axios.isAxiosError(error) || (error.response && error.response.status < 500)) {
        throw error;
      }

      await new Promise((resolve) => setTimeout(resolve, 500));
      return request();
    })
    .catch((error) => {
      courseDetailRequests.delete(key);
      throw error;
    });
  courseDetailRequests.set(key, { expiresAt: Date.now() + COURSE_DETAIL_CACHE_MS, promise });
  return promise;
}
export function prefetchCourse(id: number | string) {
  void getCourse(id).catch(() => undefined);
}
export const getSection = (id: number | string) => apiClient.get(`/sections/${id}/`, { timeout: AUTH_REQUEST_TIMEOUT });
export const createCourse = async (payload: any) => {
  const response = await apiClient.post('/courses/', payload);
  clearCourseDetailRequests();
  return response;
};
export const updateCourse = async (id: number, payload: any) => {
  const response = await apiClient.patch(`/courses/${id}/`, payload);
  clearCourseDetailRequests();
  return response;
};
export const deleteCourse = async (id: number) => {
  const response = await apiClient.delete(`/courses/${id}/`);
  clearCourseDetailRequests();
  return response;
};
export const getCategories = () => apiClient.get('/categories/', { timeout: PUBLIC_CONTENT_TIMEOUT });
export const getInstructorAnalytics = () => apiClient.get('/courses/instructor-analytics/');

export const createSection = async (payload: any) => { const response = await apiClient.post('/sections/', payload); clearCourseDetailRequests(); return response; };
export const updateSection = async (id: number, payload: any) => { const response = await apiClient.patch(`/sections/${id}/`, payload); clearCourseDetailRequests(); return response; };
export const deleteSection = async (id: number) => { const response = await apiClient.delete(`/sections/${id}/`); clearCourseDetailRequests(); return response; };

export const createLesson = async (payload: any) => { const response = await apiClient.post('/lessons/', payload); clearCourseDetailRequests(); return response; };
export const updateLesson = async (id: number, payload: any) => { const response = await apiClient.patch(`/lessons/${id}/`, payload); clearCourseDetailRequests(); return response; };
export const deleteLesson = async (id: number) => { const response = await apiClient.delete(`/lessons/${id}/`); clearCourseDetailRequests(); return response; };
export const getLesson = (id: number) => apiClient.get(`/lessons/${id}/`, { timeout: AUTH_REQUEST_TIMEOUT });
export const createResource = (payload: any) => apiClient.post('/resources/', payload);
export const uploadResource = (payload: FormData) => apiClient.post('/resources/', payload);
export const replaceVideoResources = (lesson: number, urls: string[]) => apiClient.post('/resources/replace-videos/', { lesson, urls });

// ---- Enrollments ----
export const getMyEnrollments = () => apiClient.get('/enrollments/', { timeout: AUTH_REQUEST_TIMEOUT });
export const getEnrollmentProgress = (enrollmentId: number) => apiClient.get(`/enrollments/${enrollmentId}/progress/`, { timeout: AUTH_REQUEST_TIMEOUT });
export const enroll = async (courseId: number) => {
  const response = await apiClient.post('/enrollments/', { course: courseId });
  clearCourseDetailRequests();
  return response;
};
export const markLessonComplete = (enrollmentId: number, lessonId: number) =>
  apiClient.post(`/enrollments/${enrollmentId}/mark_lesson_complete/`, { lesson_id: lessonId }, { timeout: AUTH_REQUEST_TIMEOUT });

// ---- Quizzes ----
export const createQuiz = (payload: any) => apiClient.post('/quizzes/', payload);
export const getQuiz = (id: number) => apiClient.get(`/quizzes/${id}/`);
export const getQuizzesForLesson = (lessonId: number) => apiClient.get('/quizzes/', { timeout: AUTH_REQUEST_TIMEOUT, params: { lesson: lessonId } });
export const getQuizzesForCourse = (courseId: number) => apiClient.get('/quizzes/', { timeout: AUTH_REQUEST_TIMEOUT, params: { course: courseId } });
export const updateQuiz = (id: number, payload: any) => apiClient.patch(`/quizzes/${id}/`, payload);
export const deleteQuiz = (id: number) => apiClient.delete(`/quizzes/${id}/`);
export const createQuestion = (payload: any) => apiClient.post('/questions/', payload);
export const updateQuestion = (id: number, payload: any) => apiClient.patch(`/questions/${id}/`, payload);
export const deleteQuestion = (id: number) => apiClient.delete(`/questions/${id}/`);
export const createChoice = (payload: any) => apiClient.post('/choices/', payload);
export const updateChoice = (id: number, payload: any) => apiClient.patch(`/choices/${id}/`, payload);
export const deleteChoice = (id: number) => apiClient.delete(`/choices/${id}/`);
export const submitQuiz = (quizId: number, answers: any[], durationSeconds = 0) =>
  apiClient.post(`/quizzes/${quizId}/submit/`, { answers, duration_seconds: durationSeconds });

// ---- Certificates ----
export const getMyCertificates = () => apiClient.get('/certificates/', { timeout: AUTH_REQUEST_TIMEOUT });
export const verifyCertificate = (certificateId: string) => apiClient.get(`/verify/${encodeURIComponent(certificateId)}/`);

// ---- AI Tutor ----
export const getConversations = () => apiClient.get('/ai/conversations/', { timeout: AUTH_REQUEST_TIMEOUT });
export const getConversation = (conversationId: number) => apiClient.get(`/ai/conversations/${conversationId}/`, { timeout: AUTH_REQUEST_TIMEOUT });
export const createConversation = (mode: string, title: string, course?: number) =>
  apiClient.post('/ai/conversations/', { mode, title, course }, { timeout: AUTH_REQUEST_TIMEOUT });
export const deleteConversation = (conversationId: number) => apiClient.delete(`/ai/conversations/${conversationId}/`, { timeout: AUTH_REQUEST_TIMEOUT });
export const sendAIMessage = (conversationId: number, content: string) =>
  apiClient.post(`/ai/conversations/${conversationId}/send_message/`, { content }, { timeout: 120_000 });
export const askBusinessAdvisor = (question: string) =>
  apiClient.post('/ai/advisor/', { question }, { timeout: 120_000 });

// ---- Platform services and analytics ----
export const submitServiceRequest = (payload: { service: string; notes: string }) =>
  apiClient.post('/platform/service-requests/', payload);
export const recordVisitorEvent = (path: string, session_key?: string) =>
  apiClient.post('/platform/visitor-events/', { path, session_key });
export const getAnalyticsSummary = () => apiClient.get('/platform/analytics/summary/');
export const getPlatformStats = () => apiClient.get('/platform/stats/');
