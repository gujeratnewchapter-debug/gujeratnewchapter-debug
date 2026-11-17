import { apiClient } from './api';

export type MeetingKind = 'classroom' | 'discussion' | 'consultation';
export type MeetingStatus = 'scheduled' | 'live' | 'ended' | 'cancelled';

export interface MeetingParticipant {
  id: string;
  user: string | number;
  user_name: string;
  role: string;
  joined_at: string | null;
  left_at: string | null;
  is_host: boolean;
}

export interface MeetingInvitation {
  id: string;
  meeting: string;
  invited_user: string | number;
  invited_user_name: string;
  status: 'pending' | 'accepted' | 'declined' | 'cancelled';
  created_at: string;
}

export interface Meeting {
  id: string;
  course: number | null;
  course_title: string | null;
  title: string;
  description: string;
  kind: MeetingKind;
  status: MeetingStatus;
  host: number;
  room_name: string;
  scheduled_start: string;
  scheduled_end: string | null;
  started_at: string | null;
  ended_at: string | null;
  participants: MeetingParticipant[];
  invitations: MeetingInvitation[];
  admin_notification_sent?: boolean;
}

export interface LiveKitToken {
  token: string;
  room_name: string;
  identity: string;
  url: string;
}

export interface MeetingServiceStatus {
  livekit: {
    configured: boolean;
    missing: string[];
  };
  email: {
    configured: boolean;
    missing: string[];
    provider: 'resend_api' | 'smtp';
    connection: 'connected' | 'api_configured' | 'failed' | 'not_configured';
    error: 'authentication_failed' | 'connection_failed' | null;
  };
}

export type MeetingEmailFailure =
  | 'authentication_failed'
  | 'connection_failed'
  | 'timeout'
  | 'recipient_rejected'
  | 'message_rejected'
  | 'missing_recipient_email'
  | 'not_configured'
  | 'configuration_error'
  | 'api_connection_failed'
  | 'api_unavailable'
  | 'rate_limited'
  | 'api_authentication_failed'
  | 'smtp_error'
  | 'unknown'
  | null;

export function getMeetingEmailFailureAdvice(error: MeetingEmailFailure | undefined): string {
  switch (error) {
    case 'authentication_failed':
      return 'SMTP rejected the username or password. Verify the backend email username and password.';
    case 'connection_failed':
      return 'The backend could not connect to SMTP. Verify the mail host, port, TLS settings, and provider network restrictions.';
    case 'timeout':
      return 'The SMTP server did not respond in time. Verify the mail host and port and check the provider status.';
    case 'recipient_rejected':
      return 'The SMTP server rejected the recipient address. Verify the student email and provider recipient policies.';
    case 'message_rejected':
      return 'The email provider rejected the message. Verify the sender address and sender-domain authorization.';
    case 'missing_recipient_email':
      return 'The invited student account does not have an email address.';
    case 'not_configured':
      return 'The backend email service is not configured for SMTP delivery.';
    case 'configuration_error':
      return 'The backend email service configuration is invalid. Verify the configured mail backend.';
    case 'api_connection_failed':
      return 'The backend could not connect to the HTTPS email provider. Check outbound HTTPS access and provider status.';
    case 'api_authentication_failed':
      return 'The email provider rejected its API key. Verify the backend email API secret.';
    case 'api_unavailable':
      return 'The HTTPS email provider is unavailable. Check its status and retry.';
    case 'rate_limited':
      return 'The email provider rate limit was reached. Wait before retrying.';
    case 'smtp_error':
      return 'The SMTP server rejected the request. Check the backend email logs and provider settings.';
    default:
      return 'Check the backend email logs for the delivery error.';
  }
}

const collection = '/meetings/';

export const getMeetings = (params?: Record<string, string | number>) =>
  apiClient.get(collection, { params });

export const getMeetingServiceStatus = () =>
  apiClient.get<MeetingServiceStatus>(`${collection}service-status/`);

export const getMeeting = (meetingId: string) =>
  apiClient.get<Meeting>(`${collection}${meetingId}/`);

export const createMeeting = (payload: {
  course?: number | null;
  title: string;
  description?: string;
  kind: MeetingKind;
  scheduled_start?: string;
  scheduled_end?: string | null;
}) => apiClient.post<Meeting>(collection, payload);

export const startMeeting = (meetingId: string) =>
  apiClient.post(`${collection}${meetingId}/start/`);

export const endMeeting = (meetingId: string) =>
  apiClient.post(`${collection}${meetingId}/end/`);

export const joinMeeting = (meetingId: string) =>
  apiClient.post(`${collection}${meetingId}/join/`);

export const leaveMeeting = (meetingId: string) =>
  apiClient.post(`${collection}${meetingId}/leave/`);

export const inviteMeetingUsers = (
  meetingId: string,
  emails: string[],
  studentOnly = false,
  courseStudents = false,
) => apiClient.post(`${collection}${meetingId}/invite/`, {
  emails,
  student_only: studentOnly,
  course_students: courseStudents,
});

export const getMeetingToken = (meetingId: string) =>
  apiClient.get<LiveKitToken>(`/meetings/${meetingId}/token/`);

export const requestConsultation = (meetingId: string) =>
  apiClient.post(`${collection}${meetingId}/request-consultation/`);

export const reviewConsultation = (
  meetingId: string,
  invitationId: string,
  decision: 'accept' | 'reject',
) => apiClient.post(`${collection}${meetingId}/review-consultation/`, {
  invitation_id: invitationId,
  decision,
});

export const acceptMeetingInvitation = (meetingId: string) =>
  apiClient.post(`${collection}${meetingId}/accept-invitation/`);
