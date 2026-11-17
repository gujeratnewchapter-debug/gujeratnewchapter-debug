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
    connection: 'connected' | 'failed' | 'not_configured';
    error: 'authentication_failed' | 'connection_failed' | null;
  };
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
