'use client';

import Link from 'next/link';
import { FormEvent, Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { ArrowUpRight, CalendarDays, Check, Clock3, Headphones, LoaderCircle, Plus, Radio, Users, Video, X } from 'lucide-react';
import { getCourses, getMyEnrollments } from '@/lib/api';
import {
  acceptMeetingInvitation,
  createMeeting,
  getMeetings,
  inviteMeetingUsers,
  Meeting,
  MeetingKind,
  reviewConsultation,
  requestConsultation,
} from '@/lib/meetings';
import { useAuth } from '@/lib/auth-context';
import { InnovationLoader } from '@/components/InnovationLoader';
import styles from './meetings.module.css';

type CourseOption = { id: number; title: string };
type MeetingAudience = 'individual' | 'group' | 'course';

function listFromResponse<T>(data: any): T[] {
  return data?.results ?? data ?? [];
}

function localDateTimeValue(date: Date) {
  const offset = date.getTimezoneOffset();
  return new Date(date.getTime() - offset * 60_000).toISOString().slice(0, 16);
}

function kindLabel(kind: MeetingKind) {
  return kind === 'classroom' ? 'Classroom' : kind === 'discussion' ? 'Discussion' : 'Consultation';
}

function formatMeetingTime(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value));
}

function MeetingsPageContent() {
  const { user, isBackendAuthenticated, isLoading } = useAuth();
  const searchParams = useSearchParams();
  const courseFilter = searchParams.get('course');
  const canHost = user?.role === 'instructor' || user?.role === 'mentor' || user?.role === 'super_admin';
  const isAdmin = user?.role === 'super_admin';
  const isStudent = user?.role === 'student';
  const canSchedule = canHost || isStudent;
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [courses, setCourses] = useState<CourseOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionError, setActionError] = useState('');
  const [actionSuccess, setActionSuccess] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [requestingId, setRequestingId] = useState('');
  const [reviewingId, setReviewingId] = useState('');
  const [acceptingId, setAcceptingId] = useState('');
  const [showScheduler, setShowScheduler] = useState(false);
  const [title, setTitle] = useState('');
  const [kind, setKind] = useState<MeetingKind>('classroom');
  const [meetingAudience, setMeetingAudience] = useState<MeetingAudience>('individual');
  const [courseId, setCourseId] = useState(courseFilter ?? '');
  const [startTime, setStartTime] = useState(() => localDateTimeValue(new Date(Date.now() + 60 * 60 * 1000)));
  const [description, setDescription] = useState('');
  const [inviteeEmails, setInviteeEmails] = useState('');

  const loadMeetings = useCallback(async () => {
    setError('');
    try {
      const { data } = await getMeetings();
      setMeetings(listFromResponse<Meeting>(data));
    } catch (loadError: any) {
      setError(loadError?.response?.data?.detail || 'We could not load your meeting schedule.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isBackendAuthenticated) return;
    void loadMeetings();
    if (canHost) {
      getCourses(user?.role === 'super_admin' ? undefined : { instructor: user?.id })
        .then(({ data }) => setCourses(listFromResponse<any>(data).map((course: any) => ({
          id: course.id,
          title: course.title,
        }))))
        .catch(() => setCourses([]));
    } else {
      getMyEnrollments()
        .then(({ data }) => setCourses(listFromResponse<any>(data).map((item: any) => ({
          id: item.course,
          title: item.course_detail?.title ?? `Course ${item.course}`,
        }))))
        .catch(() => setCourses([]));
    }
  }, [canHost, isBackendAuthenticated, loadMeetings, user?.id, user?.role]);

  useEffect(() => {
    setCourseId(courseFilter ?? '');
  }, [courseFilter]);

  const courseNames = useMemo(
    () => new Map(courses.map((course) => [course.id, course.title])),
    [courses],
  );
  const visibleMeetings = useMemo(
    () => meetings.filter((meeting) => !courseFilter || String(meeting.course) === courseFilter),
    [courseFilter, meetings],
  );
  const liveMeetings = visibleMeetings.filter((meeting) => meeting.status === 'live');
  const upcomingMeetings = visibleMeetings.filter((meeting) => meeting.status === 'scheduled');
  const pastMeetings = visibleMeetings.filter((meeting) => ['ended', 'cancelled'].includes(meeting.status));

  async function submitMeeting(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setActionError('');
    setActionSuccess('');
    try {
      const start = new Date(startTime);
      if (!title.trim() || Number.isNaN(start.getTime())) {
        setActionError('Add a title and a valid start time.');
        return;
      }
      const invitees = Array.from(new Set(
        inviteeEmails.split(/[,\n;]/).map((email) => email.trim().toLowerCase()).filter(Boolean),
      ));
      if (isAdmin && meetingAudience === 'individual' && invitees.length !== 1) {
        setActionError('Enter exactly one registered student email for an individual meeting.');
        return;
      }
      if (isAdmin && meetingAudience === 'group' && invitees.length === 0) {
        setActionError('Enter at least one registered student email for a group meeting.');
        return;
      }
      if (isAdmin && meetingAudience === 'course' && !courseId) {
        setActionError('Select a course to invite its enrolled students.');
        return;
      }
      if (invitees.length > 50) {
        setActionError('You can invite up to 50 people to a meeting.');
        return;
      }
      if (invitees.some((email) => !/^[^\s@,;]+@[^\s@,;]+\.[^\s@,;]+$/.test(email))) {
        setActionError('Check the invitee email addresses and try again.');
        return;
      }
      const meetingKind: MeetingKind = isAdmin
        ? meetingAudience === 'individual'
          ? 'consultation'
          : meetingAudience === 'group'
            ? 'discussion'
            : 'classroom'
        : kind;
      const { data: meeting } = await createMeeting({
        title: title.trim(),
        description: description.trim(),
        kind: meetingKind,
        course: meetingKind === 'consultation' ? null : courseId ? Number(courseId) : null,
        scheduled_start: start.toISOString(),
        scheduled_end: new Date(start.getTime() + 60 * 60 * 1000).toISOString(),
      });
      setMeetings((current) => [...current, meeting].sort(
        (a, b) => new Date(a.scheduled_start).getTime() - new Date(b.scheduled_start).getTime(),
      ));
      setTitle('');
      setDescription('');
      setInviteeEmails('');
      setShowScheduler(false);
      if (isStudent && kind === 'consultation') {
        setActionSuccess(
          meeting.admin_notification_sent
            ? `Your meeting is booked for ${formatMeetingTime(meeting.scheduled_start)}. The ESS admin team has been notified by email.`
            : `Your meeting is booked for ${formatMeetingTime(meeting.scheduled_start)}, but we could not email the admin team. Please contact ESS support.`,
        );
      } else if (invitees.length > 0 || (isAdmin && meetingAudience === 'course')) {
        try {
          const courseStudents = isAdmin && meetingAudience === 'course';
          const { data } = await inviteMeetingUsers(meeting.id, invitees, isAdmin, courseStudents);
          const invitationCount = Number(data?.invited_count)
            || (Array.isArray(data?.invitations) ? data.invitations.length : invitees.length);
          const emailDelivery = data?.email_delivery;
          if (emailDelivery?.configured && emailDelivery.sent === invitationCount && emailDelivery.failed === 0) {
            setActionSuccess(
              courseStudents
                ? `"${meeting.title}" scheduled and emailed to ${invitationCount} enrolled student${invitationCount === 1 ? '' : 's'}. They can join from the link when you start the room.`
                : `"${meeting.title}" scheduled and emailed to ${emailDelivery.sent} student${emailDelivery.sent === 1 ? '' : 's'}. They can accept the invitation from its link and join when you start the room.`,
            );
          } else {
            const sent = Number(emailDelivery?.sent) || 0;
            const failed = Number(emailDelivery?.failed) || invitationCount;
            const cause = emailDelivery?.configured
              ? `Email delivery failed for ${failed} invitee${failed === 1 ? '' : 's'}.`
              : 'The backend email service is not configured for delivery.';
            setActionError(
              `"${meeting.title}" was scheduled and access was prepared, but ${cause} Configure the backend SMTP email settings before inviting students.`,
            );
            if (sent > 0) {
              setActionSuccess(`Invitation email sent to ${sent} student${sent === 1 ? '' : 's'}.`);
            }
          }
          await loadMeetings();
        } catch (inviteError: any) {
          const reason = inviteError?.response?.data?.detail;
          setActionError(
            `"${meeting.title}" was created, but invitations could not be processed${reason ? `: ${reason}` : '. You can retry from the meeting room.'}`,
          );
        }
      } else {
        setActionSuccess(`"${meeting.title}" scheduled successfully.`);
      }
    } catch (submitError: any) {
      setActionError(submitError?.response?.data?.detail || 'We could not schedule this meeting. Check the details and try again.');
    } finally {
      setSubmitting(false);
    }
  }

  async function handleConsultationRequest(meetingId: string) {
    setRequestingId(meetingId);
    setActionError('');
    try {
      await requestConsultation(meetingId);
      await loadMeetings();
    } catch (requestError: any) {
      setActionError(requestError?.response?.data?.detail || 'Your request could not be sent.');
    } finally {
      setRequestingId('');
    }
  }

  async function handleConsultationReview(meetingId: string, invitationId: string, decision: 'accept' | 'reject') {
    setReviewingId(invitationId);
    setActionError('');
    try {
      await reviewConsultation(meetingId, invitationId, decision);
      await loadMeetings();
    } catch (reviewError: any) {
      setActionError(reviewError?.response?.data?.detail || 'We could not update this request.');
    } finally {
      setReviewingId('');
    }
  }

  async function handleAcceptInvitation(meetingId: string) {
    setAcceptingId(meetingId);
    setActionError('');
    try {
      await acceptMeetingInvitation(meetingId);
      await loadMeetings();
    } catch (acceptError: any) {
      setActionError(acceptError?.response?.data?.detail || 'We could not accept this invitation.');
    } finally {
      setAcceptingId('');
    }
  }

  if (isLoading) {
    return <div className="container section"><InnovationLoader label="Loading meetings" /></div>;
  }

  if (!isBackendAuthenticated) {
    return (
      <div className={`container section ${styles.page}`}>
        <header className={styles.pageHeader}>
          <div>
            <p className={styles.kicker}><Radio size={14} /> ESS LIVE LEARNING</p>
            <h1>Meetings</h1>
            <p className={styles.intro}>Sign in to view your schedule, book a consultation, or join a live meeting.</p>
          </div>
        </header>
        <section className={styles.emptyState}>
          <span className={styles.emptyIcon}><Headphones size={22} /></span>
          <h2>Your meeting schedule is private</h2>
          <p>Sign in with your Ethiopian Startup School account to access meetings available to you.</p>
          <button
            type="button"
            className={styles.scheduleButton}
            onClick={() => window.dispatchEvent(new CustomEvent('open-auth-modal', { detail: { returnTo: '/meetings' } }))}
          >
            Sign in to view meetings <ArrowUpRight size={16} />
          </button>
        </section>
      </div>
    );
  }

  const renderMeeting = (meeting: Meeting) => {
    const ownInvitation = meeting.invitations.find((invitation) => String(invitation.invited_user) === String(user?.id));
    const pendingRequests = canHost && meeting.kind === 'consultation' && meeting.course !== null
      ? meeting.invitations.filter((invitation) => invitation.status === 'pending')
      : [];
    const isHost = String(meeting.host) === String(user?.id) || user?.role === 'super_admin';
    const canRequest = meeting.kind === 'consultation'
      && !isHost
      && (!ownInvitation || ownInvitation.status === 'declined')
      && meeting.status === 'scheduled';
    const isParticipant = meeting.participants.some((participant) => String(participant.user) === String(user?.id));
    const joinedCount = meeting.participants.filter((participant) => participant.joined_at && !participant.left_at).length;
    const inviteCount = meeting.invitations.length;
    const hasCourseAccess = meeting.kind !== 'consultation'
      && meeting.course !== null
      && courses.some((course) => course.id === meeting.course);
    const hasAccess = isHost || isParticipant || ownInvitation?.status === 'accepted' || hasCourseAccess;
    return (
      <article className={styles.meetingRow} key={meeting.id}>
        <div className={styles.meetingMark} aria-hidden="true">
          {meeting.kind === 'consultation' ? <Headphones size={19} /> : meeting.kind === 'discussion' ? <Users size={19} /> : <Video size={19} />}
        </div>
        <div className={styles.meetingMain}>
          <div className={styles.meetingTitleLine}>
            <h3>{meeting.title}</h3>
            <span className={`${styles.kindTag} ${styles[`kind_${meeting.kind}`]}`}>{kindLabel(meeting.kind)}</span>
            {meeting.status === 'live' && <span className={styles.liveTag}><i /> Live now</span>}
          </div>
          <p className={styles.meetingMeta}>
            {formatMeetingTime(meeting.scheduled_start)}
            {meeting.course && <><span aria-hidden="true">·</span>{meeting.course_title || courseNames.get(meeting.course) || `Course ${meeting.course}`}</>}
          </p>
          {isHost && (inviteCount > 0 || joinedCount > 0) && (
            <p className={styles.attendeeSummary}>
              <Users size={13} aria-hidden="true" />
              {inviteCount} invited <span aria-hidden="true">·</span> {joinedCount} joined
            </p>
          )}
          {meeting.description && <p className={styles.meetingDescription}>{meeting.description}</p>}
          {ownInvitation?.status === 'pending' && (
            <p className={styles.requestNotice}>
              {meeting.kind === 'consultation' ? 'Your request is waiting for the host.' : 'Accept the invitation to join this meeting.'}
            </p>
          )}
          {ownInvitation?.status === 'declined' && <p className={styles.requestNotice}>The host declined this request. You can ask again.</p>}
          {ownInvitation?.status === 'accepted' && meeting.kind !== 'consultation' && <p className={styles.requestNotice}>Invitation accepted.</p>}
          {pendingRequests.length > 0 && (
            <div className={styles.requests}>
              <p>{pendingRequests.length} consultation request{pendingRequests.length === 1 ? '' : 's'}</p>
              {pendingRequests.map((invitation) => (
                <div className={styles.requestItem} key={invitation.id}>
                  <span>{invitation.invited_user_name}</span>
                  <button
                    className={styles.acceptButton}
                    disabled={reviewingId === invitation.id}
                    onClick={() => void handleConsultationReview(meeting.id, invitation.id, 'accept')}
                    aria-label={`Accept ${invitation.invited_user_name}'s request`}
                  ><Check size={15} /> Accept</button>
                  <button
                    className={styles.rejectButton}
                    disabled={reviewingId === invitation.id}
                    onClick={() => void handleConsultationReview(meeting.id, invitation.id, 'reject')}
                    aria-label={`Decline ${invitation.invited_user_name}'s request`}
                  ><X size={15} /> Decline</button>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className={styles.meetingAction}>
          {meeting.status === 'live' && hasAccess ? (
            <Link className={styles.joinButton} href={`/meetings/${meeting.id}`}>
              Join room <ArrowUpRight size={16} />
            </Link>
          ) : ownInvitation?.status === 'pending' && !isHost ? (
            <button
              className={styles.openButton}
              disabled={acceptingId === meeting.id}
              onClick={() => void handleAcceptInvitation(meeting.id)}
            >
              {acceptingId === meeting.id ? <LoaderCircle size={16} className={styles.spin} /> : <Check size={16} />}
              Accept invitation
            </button>
          ) : meeting.status === 'scheduled' && isHost ? (
            <Link className={styles.openButton} href={`/meetings/${meeting.id}`}>
              Open room <ArrowUpRight size={16} />
            </Link>
          ) : canRequest ? (
            <button
              className={styles.openButton}
              disabled={requestingId === meeting.id}
              onClick={() => void handleConsultationRequest(meeting.id)}
            >
              {requestingId === meeting.id ? <LoaderCircle size={16} className={styles.spin} /> : <Plus size={16} />}
              Request time
            </button>
          ) : meeting.status === 'scheduled' && ownInvitation?.status === 'accepted' ? (
            <span className={styles.waitingTag}>Starts {formatMeetingTime(meeting.scheduled_start)}</span>
          ) : (
            <span className={styles.waitingTag}>
              {meeting.status === 'scheduled' ? 'Waiting for host' : meeting.status === 'live' ? 'Access required' : 'Meeting ended'}
            </span>
          )}
        </div>
      </article>
    );
  };

  return (
    <div className={`container section ${styles.page}`}>
      <header className={styles.pageHeader}>
        <div>
          <p className={styles.kicker}><Radio size={14} /> ESS LIVE LEARNING</p>
          <h1>Meetings</h1>
          <p className={styles.intro}>Book a private live call with an ESS admin, or join scheduled classes and group sessions.</p>
        </div>
        {canSchedule && (
          <button className={styles.scheduleButton} onClick={() => {
            if (isStudent) setKind('consultation');
            setShowScheduler((visible) => !visible);
          }}>
            <Plus size={17} /> {isStudent ? 'Book an admin meeting' : 'Schedule a meeting'}
          </button>
        )}
      </header>

      {actionError && <p className={styles.alert} role="alert">{actionError}</p>}
      {actionSuccess && <p className={styles.successNotice} role="status">{actionSuccess}</p>}

      {showScheduler && canSchedule && (
        <form className={styles.scheduler} onSubmit={submitMeeting}>
          <div className={styles.schedulerHeader}>
            <div>
              <p className={styles.kicker}>{isStudent ? 'PRIVATE ADMIN MEETING' : 'NEW SESSION'}</p>
              <h2>{isStudent ? 'Book a live meeting with an ESS admin' : 'Put a time on the calendar'}</h2>
            </div>
            <button type="button" className={styles.closeScheduler} onClick={() => setShowScheduler(false)} aria-label="Close scheduler"><X size={18} /></button>
          </div>
          <div className={styles.formGrid}>
            <label>
              Meeting title
              <input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="e.g. Week 3 — finding your first customers" required maxLength={255} />
            </label>
            {canHost && <label>
              {isAdmin ? 'Who should attend?' : 'Session type'}
              {isAdmin ? (
                <select
                  value={meetingAudience}
                  onChange={(event) => {
                    const nextAudience = event.target.value as MeetingAudience;
                    setMeetingAudience(nextAudience);
                    setInviteeEmails('');
                    setCourseId('');
                    setKind(
                      nextAudience === 'individual'
                        ? 'consultation'
                        : nextAudience === 'group'
                          ? 'discussion'
                          : 'classroom',
                    );
                  }}
                >
                  <option value="individual">One student</option>
                  <option value="group">Selected students by email</option>
                  <option value="course">All enrolled students in a course</option>
                </select>
              ) : (
                <select value={kind} onChange={(event) => {
                  const nextKind = event.target.value as MeetingKind;
                  setKind(nextKind);
                  if (nextKind === 'consultation') setCourseId('');
                }}>
                  <option value="classroom">Live classroom</option>
                  <option value="discussion">Group discussion</option>
                  <option value="consultation">Private consultation</option>
                </select>
              )}
            </label>}
            {(isAdmin ? meetingAudience === 'course' : kind !== 'consultation') && <label>
              Course {!isAdmin && <span className={styles.optional}>optional</span>}
              <select value={courseId} onChange={(event) => setCourseId(event.target.value)}>
                {!isAdmin && <option value="">Not linked to a course</option>}
                {isAdmin && <option value="">Select a course</option>}
                {courses.map((course) => <option value={course.id} key={course.id}>{course.title}</option>)}
              </select>
            </label>}
            <label>
              Starts
              <input type="datetime-local" value={startTime} onChange={(event) => setStartTime(event.target.value)} required />
            </label>
            <label className={styles.fullWidth}>
              What will you cover?
              <textarea value={description} onChange={(event) => setDescription(event.target.value)} rows={3} maxLength={2000} placeholder="Share a little context before everyone joins." />
            </label>
            {canHost && (isAdmin ? meetingAudience !== 'course' : true) && (
              <label className={styles.fullWidth}>
                {isAdmin
                  ? meetingAudience === 'individual' ? 'Student email' : 'Student email addresses'
                  : 'Invite participants'}
                {!isAdmin && <span className={styles.optional}>optional · up to 50 emails</span>}
                <textarea
                  value={inviteeEmails}
                  onChange={(event) => setInviteeEmails(event.target.value)}
                  rows={isAdmin && meetingAudience === 'individual' ? 1 : 2}
                  maxLength={4000}
                  placeholder={isAdmin && meetingAudience === 'individual'
                    ? 'student@example.com'
                    : 'student1@example.com, student2@example.com'}
                  required={isAdmin}
                  aria-describedby="meeting-invite-hint"
                />
                <span className={styles.inviteHint} id="meeting-invite-hint">
                  {isAdmin
                    ? meetingAudience === 'individual'
                      ? 'The address must belong to a registered student. They must accept the invitation before joining.'
                      : 'Enter registered student email addresses, separated by commas or new lines. Each student must accept before joining.'
                    : kind === 'consultation'
                      ? 'Invite the student by email. They must accept before joining.'
                      : 'Invite registered ESS members by email. Course enrollment remains another way to join.'}
                </span>
              </label>
            )}
            {isAdmin && meetingAudience === 'course' && (
              <p className={styles.inviteHint}>
                An invitation email with the meeting link will be sent to every active student enrolled in the selected course.
              </p>
            )}
          </div>
          {actionError && <p className={styles.formError} role="alert">{actionError}</p>}
          <div className={styles.schedulerFooter}>
            <span><Clock3 size={15} /> 60-minute session</span>
            <button type="submit" className={styles.scheduleButton} disabled={submitting}>
              {submitting ? <LoaderCircle size={16} className={styles.spin} /> : <CalendarDays size={16} />}
              Schedule
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <div className={styles.listLoading}><InnovationLoader label="Loading your schedule" /></div>
      ) : error ? (
        <div className={styles.emptyState}>
          <div className={styles.emptyIcon}><Radio size={22} /></div>
          <h2>Schedule unavailable</h2>
          <p>{error}</p>
          <button className={styles.openButton} onClick={() => { setLoading(true); void loadMeetings(); }}>Try again</button>
        </div>
      ) : (
        <div className={styles.scheduleLayout}>
          <div className={styles.scheduleList}>
            {liveMeetings.length > 0 && (
              <section className={styles.sectionBlock}>
                <div className={styles.sectionHeading}><span className={styles.liveIndicator} /><h2>Happening now</h2><span>{liveMeetings.length}</span></div>
                <div className={styles.meetingList}>{liveMeetings.map(renderMeeting)}</div>
              </section>
            )}
            <section className={styles.sectionBlock}>
              <div className={styles.sectionHeading}><CalendarDays size={17} /><h2>Coming up</h2><span>{upcomingMeetings.length}</span></div>
              {upcomingMeetings.length > 0
                ? <div className={styles.meetingList}>{upcomingMeetings.map(renderMeeting)}</div>
                : liveMeetings.length === 0 && <div className={styles.emptyState}>
                  <div className={styles.emptyIcon}><CalendarDays size={22} /></div>
                  <h2>Your next session starts here</h2>
                  <p>{canHost ? 'Schedule a classroom, discussion, or private consultation.' : 'New classes and mentor sessions will appear here.'}</p>
                  {canSchedule && <button className={styles.openButton} onClick={() => {
                    if (isStudent) setKind('consultation');
                    setShowScheduler(true);
                  }}><Plus size={16} /> {isStudent ? 'Book an admin meeting' : 'Create a session'}</button>}
                  {!canHost && <Link className={styles.openButton} href="/courses">Explore courses <ArrowUpRight size={16} /></Link>}
                </div>}
            </section>
            {pastMeetings.length > 0 && (
              <section className={styles.sectionBlock}>
                <div className={styles.sectionHeading}><Clock3 size={17} /><h2>Past sessions</h2><span>{pastMeetings.length}</span></div>
                <div className={styles.meetingList}>{pastMeetings.map(renderMeeting)}</div>
              </section>
            )}
          </div>
          <aside className={styles.sideNote}>
            <div className={styles.sideNoteMark}><Video size={19} /></div>
            <p className={styles.kicker}>BE READY TO JOIN</p>
            <h2>A small check-in before the big ideas.</h2>
            <ul>
              <li>Use headphones for clearer conversation.</li>
              <li>Allow camera and microphone access when asked.</li>
              <li>Join a minute early to check your setup.</li>
            </ul>
            <Link href="/courses" className={styles.textLink}>Browse your learning paths <ArrowUpRight size={15} /></Link>
          </aside>
        </div>
      )}
    </div>
  );
}

export default function MeetingsPage() {
  return (
    <Suspense fallback={<div className="container section"><InnovationLoader label="Loading meetings" /></div>}>
      <MeetingsPageContent />
    </Suspense>
  );
}
