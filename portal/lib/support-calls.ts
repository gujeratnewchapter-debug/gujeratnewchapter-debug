import { apiClient } from './api';

export type SupportCallMode = 'audio' | 'video';
export type SupportCallStatus = 'pending' | 'accepted' | 'rejected' | 'ended' | 'expired';
export type SupportCallDirection = 'student_to_admin' | 'admin_to_student';

export interface SupportCallAccess {
  call_id: string;
  capability: string;
  status: 'pending';
  expires_at: string;
}

export interface SupportCallState {
  call_id: string;
  status: SupportCallStatus;
  mode: SupportCallMode;
  display_name: string;
  accepted_at: string | null;
  expires_at: string;
  email?: string;
  question?: string;
  mode_label?: string;
  direction?: SupportCallDirection;
  direction_label?: string;
  recipient_id?: number | null;
  created_at?: string;
}

export interface SupportCallStudent {
  id: number;
  first_name: string;
  last_name: string;
  username: string;
  email: string;
}

export interface SupportCallStudentAccess {
  call_id: string;
  display_name: string;
  question: string;
  mode: SupportCallMode;
  mode_label: string;
  status: SupportCallStatus;
  accepted_at: string | null;
  created_at: string;
  expires_at: string;
}

export interface SupportCallCredentials {
  token: string;
  url: string;
}

export interface SupportCallAdminSession {
  call_id: string;
  capability: string;
}

export function createSupportCall(payload: {
  display_name: string;
  email: string;
  question?: string;
  mode: SupportCallMode;
}) {
  return apiClient.post<SupportCallAccess>('/support-calls/requests/', payload);
}

export function getSupportCallStatus(callId: string, capability: string) {
  return apiClient.post<SupportCallState>('/support-calls/status/', {
    call_id: callId,
    capability,
  });
}

export function getSupportCallToken(callId: string, capability: string) {
  return apiClient.post<SupportCallCredentials>('/support-calls/token/', {
    call_id: callId,
    capability,
  });
}

export function getAdminSupportCalls() {
  return apiClient.get<SupportCallState[]>('/support-calls/admin/');
}

export function getAdminSupportCallStudents() {
  return apiClient.get<SupportCallStudent[]>('/support-calls/admin/students/');
}

export function createAdminStudentSupportCall(studentId: number, mode: SupportCallMode) {
  return apiClient.post<SupportCallState>('/support-calls/admin/outbound/', { student_id: studentId, mode });
}

export function getStudentSupportCalls() {
  return apiClient.get<SupportCallStudentAccess[]>('/support-calls/student/');
}

export function getStudentSupportCall(callId: string) {
  return apiClient.get<SupportCallStudentAccess>(`/support-calls/student/${callId}/`);
}

export function takeStudentSupportCallAction(callId: string, action: 'accept' | 'reject') {
  return apiClient.post<SupportCallStudentAccess>(`/support-calls/student/${callId}/${action}/`);
}

export function getStudentSupportCallToken(callId: string) {
  return apiClient.post<SupportCallCredentials>(`/support-calls/student/${callId}/token/`);
}

export function getAdminSupportCall(callId: string) {
  return apiClient.get<SupportCallState>(`/support-calls/admin/${callId}/`);
}

export function takeSupportCallAction(callId: string, action: 'accept' | 'reject' | 'end') {
  return apiClient.post<SupportCallState>(`/support-calls/admin/${callId}/${action}/`);
}

export function getAdminSupportCallToken(callId: string) {
  return apiClient.post<SupportCallCredentials>(`/support-calls/admin/${callId}/token/`);
}

export function createAdminSupportCallSession(callId: string) {
  return apiClient.post<SupportCallAdminSession>(`/support-calls/admin/${callId}/session-ticket/`);
}

export function getAdminSessionCall(callId: string, capability: string) {
  return apiClient.post<SupportCallState>(`/support-calls/admin-session/${callId}/status/`, { capability });
}

export function getAdminSessionCallToken(callId: string, capability: string) {
  return apiClient.post<SupportCallCredentials>(`/support-calls/admin-session/${callId}/token/`, { capability });
}

export function endAdminSessionCall(callId: string, capability: string) {
  return apiClient.post<SupportCallState>(`/support-calls/admin-session/${callId}/end/`, { capability });
}

export function getSupportCallError(error: unknown, fallback: string) {
  const response = (error as { response?: { data?: { detail?: unknown } } })?.response;
  return typeof response?.data?.detail === 'string' ? response.data.detail : fallback;
}
