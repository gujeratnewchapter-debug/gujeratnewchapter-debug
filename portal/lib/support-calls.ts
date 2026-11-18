import { apiClient } from './api';

export type SupportCallMode = 'audio' | 'video';
export type SupportCallStatus = 'pending' | 'accepted' | 'rejected' | 'ended' | 'expired';

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
  created_at?: string;
}

export interface SupportCallCredentials {
  token: string;
  url: string;
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

export function getAdminSupportCall(callId: string) {
  return apiClient.get<SupportCallState>(`/support-calls/admin/${callId}/`);
}

export function takeSupportCallAction(callId: string, action: 'accept' | 'reject' | 'end') {
  return apiClient.post<SupportCallState>(`/support-calls/admin/${callId}/${action}/`);
}

export function getAdminSupportCallToken(callId: string) {
  return apiClient.post<SupportCallCredentials>(`/support-calls/admin/${callId}/token/`);
}

export function getSupportCallError(error: unknown, fallback: string) {
  const response = (error as { response?: { data?: { detail?: unknown } } })?.response;
  return typeof response?.data?.detail === 'string' ? response.data.detail : fallback;
}
