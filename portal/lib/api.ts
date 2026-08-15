import axios from 'axios';
import { supabase } from './supabase';
import { getStoredDjangoAccessToken, isUsableJwtToken } from './auth-token';

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';

export const apiClient = axios.create({ baseURL: API_BASE_URL, timeout: 15000 });

apiClient.interceptors.request.use(async (config) => {
  const djangoToken = getStoredDjangoAccessToken();
  const headers = config.headers ?? {};

  if (djangoToken && isUsableJwtToken(djangoToken)) {
    (headers as Record<string, string>).Authorization = `Bearer ${djangoToken}`;
  } else {
    delete (headers as Record<string, string>).Authorization;
  }

  config.headers = headers;
  return config;
});

apiClient.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    const status = error.response?.status;

    if (status === 401 && !original._retry) {
      original._retry = true;
      clearDjangoAuthToken();
      return Promise.reject(error);
    }

    if (status === 403) {
      // 403 Forbidden may mean either unauthenticated or lacks permission.
      // Only clear token if we detect it's actually invalid.
      const djangoToken = getStoredDjangoAccessToken();
      if (!djangoToken || !isUsableJwtToken(djangoToken)) {
        clearDjangoAuthToken();
      }
    }

    return Promise.reject(error);
  }
);

// ---- Auth ----
export const register = (payload: {
  username?: string; email: string; password: string;
  first_name?: string; last_name?: string; full_name?: string;
  role: 'student' | 'instructor';
}) => apiClient.post('/auth/register/', payload);

export const login = (username: string, password: string) =>
  apiClient.post('/auth/login/', { username, password });

export const googleLogin = (id_token: string, role: 'student' | 'instructor' = 'student') =>
  apiClient.post('/auth/login/google/', { id_token, role });

export function setDjangoAuthToken(accessToken: string | null) {
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
  try { localStorage.removeItem('django_access'); localStorage.removeItem('django_refresh'); } catch (e) { /* ignore */ }
}

export const verifyEmail = (token: string) => apiClient.post('/auth/verify-email/', { token });
export const resendVerification = () => apiClient.post('/auth/resend-verification/');
export const getMe = () => apiClient.get('/auth/me/');
export const updateMe = (payload: any) => apiClient.patch('/auth/me/', payload);

// ---- Site settings ----
export const getSiteSettings = () => apiClient.get('/site-settings/');

// ---- Courses ----
export const getCourses = (params?: Record<string, any>) => apiClient.get('/courses/', { params });
export const getCourse = (id: number | string) => apiClient.get(`/courses/${id}/`);
export const getSection = (id: number | string) => apiClient.get(`/sections/${id}/`);
export const createCourse = (payload: any) => apiClient.post('/courses/', payload);
export const updateCourse = (id: number, payload: any) => apiClient.patch(`/courses/${id}/`, payload);
export const getCategories = () => apiClient.get('/categories/');

export const createSection = (payload: any) => apiClient.post('/sections/', payload);
export const updateSection = (id: number, payload: any) => apiClient.patch(`/sections/${id}/`, payload);
export const deleteSection = (id: number) => apiClient.delete(`/sections/${id}/`);

export const createLesson = (payload: any) => apiClient.post('/lessons/', payload);
export const updateLesson = (id: number, payload: any) => apiClient.patch(`/lessons/${id}/`, payload);
export const deleteLesson = (id: number) => apiClient.delete(`/lessons/${id}/`);
export const getLesson = (id: number) => apiClient.get(`/lessons/${id}/`);

// ---- Enrollments ----
export const getMyEnrollments = () => apiClient.get('/enrollments/');
export const enroll = (courseId: number) => apiClient.post('/enrollments/', { course: courseId });
export const markLessonComplete = (enrollmentId: number, lessonId: number) =>
  apiClient.post(`/enrollments/${enrollmentId}/mark_lesson_complete/`, { lesson_id: lessonId });

// ---- Quizzes ----
export const createQuiz = (payload: any) => apiClient.post('/quizzes/', payload);
export const getQuiz = (id: number) => apiClient.get(`/quizzes/${id}/`);
export const getQuizzesForLesson = (lessonId: number) => apiClient.get('/quizzes/', { params: { lesson: lessonId } });
export const updateQuiz = (id: number, payload: any) => apiClient.patch(`/quizzes/${id}/`, payload);
export const deleteQuiz = (id: number) => apiClient.delete(`/quizzes/${id}/`);
export const createQuestion = (payload: any) => apiClient.post('/questions/', payload);
export const updateQuestion = (id: number, payload: any) => apiClient.patch(`/questions/${id}/`, payload);
export const deleteQuestion = (id: number) => apiClient.delete(`/questions/${id}/`);
export const createChoice = (payload: any) => apiClient.post('/choices/', payload);
export const updateChoice = (id: number, payload: any) => apiClient.patch(`/choices/${id}/`, payload);
export const deleteChoice = (id: number) => apiClient.delete(`/choices/${id}/`);
export const submitQuiz = (quizId: number, answers: any[]) =>
  apiClient.post(`/quizzes/${quizId}/submit/`, { answers });

// ---- Certificates ----
export const getMyCertificates = () => apiClient.get('/certificates/');
export const verifyCertificate = (certificateId: string) => apiClient.get(`/verify/${encodeURIComponent(certificateId)}/`);

// ---- AI Tutor ----
export const getConversations = () => apiClient.get('/ai/conversations/');
export const createConversation = (mode: string, title: string, course?: number) =>
  apiClient.post('/ai/conversations/', { mode, title, course });
export const sendAIMessage = (conversationId: number, content: string) =>
  apiClient.post(`/ai/conversations/${conversationId}/send_message/`, { content });
