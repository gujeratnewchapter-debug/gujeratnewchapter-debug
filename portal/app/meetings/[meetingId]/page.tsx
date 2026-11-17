'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { FormEvent, useCallback, useEffect, useRef, useState } from 'react';
import {
  ArrowLeft,
  BookOpen,
  Check,
  CircleHelp,
  Clock3,
  Expand,
  Headphones,
  LoaderCircle,
  MessageCircle,
  Mic,
  MicOff,
  MonitorUp,
  PhoneOff,
  Send,
  ShieldCheck,
  Users,
  UserPlus,
  Video,
  VideoOff,
  Wifi,
  WifiOff,
  X,
} from 'lucide-react';
import { ConnectionState, Room, RoomEvent, Track } from 'livekit-client';
import { useAuth } from '@/lib/auth-context';
import {
  acceptMeetingInvitation,
  endMeeting,
  getMeeting,
  getMeetingToken,
  inviteMeetingUsers,
  joinMeeting,
  leaveMeeting,
  Meeting,
  startMeeting,
} from '@/lib/meetings';
import styles from './page.module.css';

type RoomPhase = 'idle' | 'connecting' | 'connected' | 'reconnecting' | 'disconnected' | 'ended';
type ChatMessage = { id: string; name: string; text: string; time: string; mine: boolean };
type RoomDataMessage =
  | { type: 'chat'; text: string; name: string; id: string }
  | { type: 'hand'; raised: boolean };

function getErrorMessage(error: unknown, fallback: string) {
  const response = (error as { response?: { data?: { detail?: unknown } } })?.response;
  return typeof response?.data?.detail === 'string' ? response.data.detail : fallback;
}

function mediaErrorMessage(error: unknown) {
  const name = (error as { name?: string })?.name;
  if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
    return 'Permission was denied. Allow camera or microphone access in your browser settings, then try again.';
  }
  if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
    return 'No matching device was found. Connect a camera or microphone and try again.';
  }
  if (name === 'NotReadableError' || name === 'TrackStartError') {
    return 'The device could not be opened. It may be in use by another application.';
  }
  if (name === 'SecurityError') {
    return 'Media access requires a secure page. Open this site over HTTPS or localhost.';
  }
  return 'The device could not be started. Check browser permissions and device settings, then try again.';
}

function initials(name: string) {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join('').toUpperCase() || '?';
}

function formatElapsed(seconds: number) {
  const safeSeconds = Math.max(0, seconds);
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  const remainder = safeSeconds % 60;
  return [hours, minutes, remainder].map((value) => String(value).padStart(2, '0')).join(':');
}

function formatClock(date: Date) {
  return new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(date);
}

function getVideoTrack(participant: any) {
  const publications = Array.from(participant.videoTrackPublications.values()) as any[];
  return publications.find((publication) => publication.source === Track.Source.ScreenShare && publication.track)?.track
    || publications.find((publication) => publication.source === Track.Source.Camera && publication.track)?.track;
}

function VideoSurface({ track, name, local, large }: {
  track?: any;
  name: string;
  local: boolean;
  large?: boolean;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (!track || !videoRef.current) return;
    const element = track.attach(videoRef.current);
    return () => {
      track.detach(element);
    };
  }, [track]);

  return (
    <div className={`${styles.videoSurface} ${large ? styles.screenSurface : ''}`}>
      {track ? (
        <video ref={videoRef} autoPlay playsInline muted={local} />
      ) : (
        <div className={styles.avatar} aria-hidden="true">{initials(name)}</div>
      )}
      <div className={styles.tileLabel}>
        <span>{name}{local ? ' · You' : ''}</span>
      </div>
    </div>
  );
}

function AudioOutput({ track }: { track: any }) {
  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    if (!track || !audioRef.current) return;
    const element = track.attach(audioRef.current);
    return () => {
      track.detach(element);
    };
  }, [track]);

  return <audio ref={audioRef} autoPlay />;
}

export default function MeetingRoomPage({ params }: { params: { meetingId: string } }) {
  const meetingId = params.meetingId;
  const router = useRouter();
  const { user, isBackendAuthenticated, isLoading: authLoading } = useAuth();
  const [meeting, setMeeting] = useState<Meeting | null>(null);
  const [loading, setLoading] = useState(true);
  const [room, setRoom] = useState<Room | null>(null);
  const [roomPhase, setRoomPhase] = useState<RoomPhase>('idle');
  const [actionBusy, setActionBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [mediaError, setMediaError] = useState('');
  const [microphoneOn, setMicrophoneOn] = useState(false);
  const [cameraOn, setCameraOn] = useState(false);
  const [screenShareOn, setScreenShareOn] = useState(false);
  const [mediaBusy, setMediaBusy] = useState(false);
  const [mediaSupported, setMediaSupported] = useState({ audioVideo: false, screenShare: false });
  const [chatOpen, setChatOpen] = useState(false);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteEmails, setInviteEmails] = useState('');
  const [inviteBusy, setInviteBusy] = useState(false);
  const [inviteError, setInviteError] = useState('');
  const [inviteNotice, setInviteNotice] = useState('');
  const [acceptingInvitation, setAcceptingInvitation] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatDraft, setChatDraft] = useState('');
  const [unreadCount, setUnreadCount] = useState(0);
  const [handRaised, setHandRaised] = useState(false);
  const [raisedHands, setRaisedHands] = useState<Record<string, boolean>>({});
  const [activeSpeakers, setActiveSpeakers] = useState<string[]>([]);
  const [, setParticipantVersion] = useState(0);
  const [elapsedNow, setElapsedNow] = useState(Date.now());
  const [connectedAt, setConnectedAt] = useState<number | null>(null);
  const [fullscreen, setFullscreen] = useState(false);
  const joinedRef = useRef(false);
  const manualDisconnectRef = useRef(false);
  const terminalStatusRef = useRef(false);
  const roomRef = useRef<Room | null>(null);
  const chatOpenRef = useRef(false);
  const handRaisedRef = useRef(false);

  const isHost = Boolean(
    meeting && user && (String(meeting.host) === String(user.id) || user.role === 'super_admin'),
  );
  const isLive = meeting?.status === 'live';
  const hasPendingInvitation = Boolean(
    meeting?.invitations.some(
      (invitation) => String(invitation.invited_user) === String(user?.id) && invitation.status === 'pending',
    ),
  );

  const loadMeeting = useCallback(async () => {
    const { data } = await getMeeting(meetingId);
    if (!terminalStatusRef.current) setMeeting(data);
    return data as Meeting;
  }, [meetingId]);

  useEffect(() => {
    if (!isBackendAuthenticated) {
      if (!authLoading) setLoading(false);
      return;
    }

    let active = true;
    setLoading(true);
    setError('');
    getMeeting(meetingId).then(({ data }) => {
      if (active) setMeeting(data);
    }).catch((loadError: unknown) => {
      if (active) setError(getErrorMessage(loadError, 'This meeting could not be found or you do not have access.'));
    }).finally(() => {
      if (active) setLoading(false);
    });

    return () => {
      active = false;
    };
  }, [authLoading, isBackendAuthenticated, meetingId]);

  useEffect(() => {
    if (typeof navigator === 'undefined') return;
    const devices = navigator.mediaDevices;
    setMediaSupported({
      audioVideo: Boolean(devices && typeof devices.getUserMedia === 'function'),
      screenShare: Boolean(devices && typeof devices.getDisplayMedia === 'function'),
    });
  }, []);

  useEffect(() => {
    const handleFullscreen = () => setFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener('fullscreenchange', handleFullscreen);
    return () => document.removeEventListener('fullscreenchange', handleFullscreen);
  }, []);

  useEffect(() => {
    chatOpenRef.current = chatOpen;
  }, [chatOpen]);

  useEffect(() => {
    handRaisedRef.current = handRaised;
  }, [handRaised]);

  useEffect(() => {
    if (!meeting || !['live', 'scheduled'].includes(meeting.status) || !isBackendAuthenticated) return;
    let active = true;
    const interval = window.setInterval(async () => {
      try {
        const latest = await loadMeeting();
        if (!active || !['ended', 'cancelled'].includes(latest.status)) return;
        terminalStatusRef.current = true;
        manualDisconnectRef.current = true;
        await roomRef.current?.disconnect();
        roomRef.current = null;
        setRoom(null);
        setRoomPhase('ended');
        setNotice(latest.status === 'cancelled' ? 'The host cancelled this meeting.' : 'This meeting has ended.');
        if (joinedRef.current) {
          joinedRef.current = false;
          void leaveMeeting(meetingId).catch(() => undefined);
        }
      } catch {
        // A temporary API outage should not interrupt an active LiveKit room.
      }
    }, meeting.status === 'scheduled' ? 6000 : 12000);

    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, [isBackendAuthenticated, loadMeeting, meeting, meetingId]);

  useEffect(() => {
    const timer = window.setInterval(() => setElapsedNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => () => {
    manualDisconnectRef.current = true;
    const currentRoom = roomRef.current;
    roomRef.current = null;
    if (currentRoom) void currentRoom.disconnect();
    if (joinedRef.current) {
      joinedRef.current = false;
      void leaveMeeting(meetingId).catch(() => undefined);
    }
  }, [meetingId]);

  const participants = room
    ? [room.localParticipant as any, ...Array.from(room.remoteParticipants.values()) as any[]]
    : [];

  const localParticipant = room?.localParticipant;
  const durationStart = meeting?.started_at ? new Date(meeting.started_at).getTime() : connectedAt;
  const duration = durationStart ? Math.floor((elapsedNow - durationStart) / 1000) : 0;
  const phaseLabel = roomPhase === 'reconnecting'
    ? 'Reconnecting'
    : roomPhase === 'connected'
      ? 'Connected'
      : roomPhase === 'connecting'
        ? 'Connecting'
        : roomPhase === 'disconnected'
          ? 'Connection closed'
          : meeting?.status === 'scheduled'
            ? 'Waiting for host'
            : 'Ready when you are';

  function installRoomEvents(nextRoom: Room) {
    const updateParticipants = () => setParticipantVersion((current) => current + 1);
    nextRoom.on(RoomEvent.ConnectionStateChanged, (state) => {
      if (state === ConnectionState.Reconnecting) setRoomPhase('reconnecting');
      if (state === ConnectionState.Connected) setRoomPhase('connected');
      updateParticipants();
    });
    nextRoom.on(RoomEvent.Reconnecting, () => setRoomPhase('reconnecting'));
    nextRoom.on(RoomEvent.Reconnected, () => {
      setRoomPhase('connected');
      setNotice('Connection restored.');
      updateParticipants();
      const state = JSON.stringify({ type: 'hand', raised: handRaisedRef.current } satisfies RoomDataMessage);
      void nextRoom.localParticipant.publishData(new TextEncoder().encode(state), {
        reliable: true,
        topic: 'ess-meeting-hand',
      }).catch(() => undefined);
    });
    nextRoom.on(RoomEvent.Connected, () => {
      setRoomPhase('connected');
      updateParticipants();
    });
    nextRoom.on(RoomEvent.Disconnected, () => {
      if (manualDisconnectRef.current || terminalStatusRef.current) return;
      setRoomPhase('disconnected');
      setError('Your connection to the room closed. You can try joining again.');
      updateParticipants();
    });
    nextRoom.on(RoomEvent.ParticipantConnected, updateParticipants);
    nextRoom.on(RoomEvent.ParticipantDisconnected, (participant) => {
      setRaisedHands((current) => {
        const next = { ...current };
        delete next[participant.identity];
        return next;
      });
      updateParticipants();
    });
    nextRoom.on(RoomEvent.TrackSubscribed, updateParticipants);
    nextRoom.on(RoomEvent.TrackUnsubscribed, updateParticipants);
    nextRoom.on(RoomEvent.TrackPublished, updateParticipants);
    nextRoom.on(RoomEvent.TrackUnpublished, updateParticipants);
    nextRoom.on(RoomEvent.TrackMuted, updateParticipants);
    nextRoom.on(RoomEvent.TrackUnmuted, updateParticipants);
    nextRoom.on(RoomEvent.LocalTrackPublished, updateParticipants);
    nextRoom.on(RoomEvent.LocalTrackUnpublished, (publication) => {
      if (publication.source === Track.Source.Microphone) setMicrophoneOn(false);
      if (publication.source === Track.Source.Camera) setCameraOn(false);
      if (publication.source === Track.Source.ScreenShare) setScreenShareOn(false);
      updateParticipants();
    });
    nextRoom.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
      setActiveSpeakers(speakers.map((speaker) => speaker.identity));
      updateParticipants();
    });
    nextRoom.on(RoomEvent.DataReceived, (payload, participant, _kind, topic) => {
      if (!participant) return;
      try {
        const message = JSON.parse(new TextDecoder().decode(payload)) as RoomDataMessage;
        if (topic === 'ess-meeting-chat' && message.type === 'chat' && message.text) {
          setMessages((current) => [...current.slice(-99), {
            id: message.id,
            name: message.name || participant.name || participant.identity,
            text: message.text.slice(0, 1500),
            time: formatClock(new Date()),
            mine: false,
          }]);
          setUnreadCount((count) => chatOpenRef.current ? count : count + 1);
        }
        if (topic === 'ess-meeting-hand' && message.type === 'hand') {
          setRaisedHands((current) => ({ ...current, [participant.identity]: message.raised }));
        }
      } catch {
        // Ignore malformed room data from clients that are not using this chat protocol.
      }
    });
    nextRoom.on(RoomEvent.MediaDevicesError, (deviceError) => setMediaError(mediaErrorMessage(deviceError)));
  }

  async function connectToRoom(startFirst = false) {
    if (!meeting || actionBusy) return;
    setActionBusy(true);
    setError('');
    setNotice('');
    setMediaError('');
    setRoomPhase('connecting');
    manualDisconnectRef.current = false;
    terminalStatusRef.current = false;
    let joined = false;
    let nextRoom: Room | null = null;

    try {
      if (startFirst) {
        if (!isHost || meeting.status !== 'scheduled') {
          throw new Error('Only the meeting host can start a scheduled meeting.');
        }
        await startMeeting(meetingId);
        await loadMeeting();
      }
      await joinMeeting(meetingId);
      joined = true;
      joinedRef.current = true;
      const { data: credentials } = await getMeetingToken(meetingId);
      if (!credentials?.token || !credentials?.url) {
        throw new Error('The meeting service did not return valid connection details.');
      }
      nextRoom = new Room({ adaptiveStream: true, dynacast: true });
      roomRef.current = nextRoom;
      installRoomEvents(nextRoom);
      await nextRoom.connect(credentials.url, credentials.token);
      setRoom(nextRoom);
      setRoomPhase('connected');
      setConnectedAt(Date.now());
      setParticipantVersion((current) => current + 1);
    } catch (connectError: unknown) {
      if (nextRoom) {
        manualDisconnectRef.current = true;
        await nextRoom.disconnect().catch(() => undefined);
      }
      if (roomRef.current === nextRoom) roomRef.current = null;
      if (joined) {
        joinedRef.current = false;
        await leaveMeeting(meetingId).catch(() => undefined);
      }
      setRoom(null);
      setRoomPhase(meeting.status === 'live' || startFirst ? 'disconnected' : 'idle');
      setError(getErrorMessage(
        connectError,
        'We could not connect to this meeting. Check your connection and try again.',
      ));
      if (startFirst) {
        void loadMeeting().catch(() => undefined);
      }
    } finally {
      setActionBusy(false);
    }
  }

  async function leaveRoom(endForEveryone = false) {
    if (actionBusy) return;
    setActionBusy(true);
    setError('');
    setNotice('');
    try {
      if (endForEveryone) {
        if (!isHost) throw new Error('Only the host can end this meeting.');
        terminalStatusRef.current = true;
        await endMeeting(meetingId);
        setMeeting((current) => current ? { ...current, status: 'ended', ended_at: new Date().toISOString() } : current);
        setRoomPhase('ended');
        setNotice('Meeting ended for everyone.');
      }
      manualDisconnectRef.current = true;
      const currentRoom = roomRef.current;
      roomRef.current = null;
      await currentRoom?.disconnect();
      setRoom(null);
      if (joinedRef.current) {
        joinedRef.current = false;
        await leaveMeeting(meetingId);
      }
      if (!endForEveryone) router.push('/meetings');
    } catch (leaveError: unknown) {
      if (endForEveryone) terminalStatusRef.current = false;
      setError(getErrorMessage(leaveError, 'We could not complete that meeting action. Please try again.'));
    } finally {
      setActionBusy(false);
    }
  }

  async function toggleMicrophone() {
    if (!room || mediaBusy) return;
    if (!mediaSupported.audioVideo) {
      setMediaError('This browser does not support microphone access. Try a current browser over HTTPS or localhost.');
      return;
    }
    setMediaBusy(true);
    setMediaError('');
    try {
      await room.localParticipant.setMicrophoneEnabled(!microphoneOn);
      setMicrophoneOn(!microphoneOn);
      setParticipantVersion((current) => current + 1);
    } catch (deviceError: unknown) {
      setMediaError(mediaErrorMessage(deviceError));
    } finally {
      setMediaBusy(false);
    }
  }

  async function toggleCamera() {
    if (!room || mediaBusy) return;
    if (!mediaSupported.audioVideo) {
      setMediaError('This browser does not support camera access. Try a current browser over HTTPS or localhost.');
      return;
    }
    setMediaBusy(true);
    setMediaError('');
    try {
      await room.localParticipant.setCameraEnabled(!cameraOn);
      setCameraOn(!cameraOn);
      setParticipantVersion((current) => current + 1);
    } catch (deviceError: unknown) {
      setMediaError(mediaErrorMessage(deviceError));
    } finally {
      setMediaBusy(false);
    }
  }

  async function toggleScreenShare() {
    if (!room || mediaBusy) return;
    if (!mediaSupported.screenShare) {
      setMediaError('Screen sharing is not available in this browser or page context.');
      return;
    }
    setMediaBusy(true);
    setMediaError('');
    try {
      await room.localParticipant.setScreenShareEnabled(!screenShareOn);
      setScreenShareOn(!screenShareOn);
      setParticipantVersion((current) => current + 1);
    } catch (deviceError: unknown) {
      setMediaError(mediaErrorMessage(deviceError));
    } finally {
      setMediaBusy(false);
    }
  }

  async function toggleRaisedHand() {
    if (!room) return;
    const raised = !handRaised;
    const payload = JSON.stringify({ type: 'hand', raised } satisfies RoomDataMessage);
    try {
      await room.localParticipant.publishData(new TextEncoder().encode(payload), {
        reliable: true,
        topic: 'ess-meeting-hand',
      });
      setHandRaised(raised);
      handRaisedRef.current = raised;
      setRaisedHands((current) => ({ ...current, [room.localParticipant.identity]: raised }));
    } catch {
      setError('Your hand could not be sent. Check your connection and try again.');
    }
  }

  async function sendChat(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = chatDraft.trim();
    if (!room || !text || text.length > 1500) return;
    const message = {
      type: 'chat',
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      name: user ? `${user.first_name} ${user.last_name}`.trim() || user.username : 'You',
      text,
    } satisfies RoomDataMessage;
    try {
      await room.localParticipant.publishData(new TextEncoder().encode(JSON.stringify(message)), {
        reliable: true,
        topic: 'ess-meeting-chat',
      });
      setMessages((current) => [...current.slice(-99), {
        id: message.id,
        name: message.name,
        text,
        time: formatClock(new Date()),
        mine: true,
      }]);
      setChatDraft('');
    } catch {
      setError('Your message could not be sent. Check your connection and try again.');
    }
  }

  async function sendInvitations(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const emails = Array.from(new Set(
      inviteEmails.split(/[,\n;]/).map((email) => email.trim()).filter(Boolean),
    ));
    if (!emails.length) {
      setInviteError('Enter at least one participant email address.');
      return;
    }
    if (emails.length > 50) {
      setInviteError('You can invite up to 50 people at a time.');
      return;
    }

    setInviteBusy(true);
    setInviteError('');
    setInviteNotice('');
    try {
      const { data } = await inviteMeetingUsers(meetingId, emails);
      const delivery = data.email_delivery;
      if (delivery?.configured && delivery.sent === emails.length && delivery.failed === 0) {
        setInviteNotice(`${delivery.sent} invitation email${delivery.sent === 1 ? '' : 's'} sent. Invitees can open the link, accept, and join when the room is live.`);
      } else {
        setInviteError(
          delivery?.configured
            ? `Invitations were saved, but email delivery failed for ${delivery.failed || emails.length} recipient${(delivery.failed || emails.length) === 1 ? '' : 's'}. Check the backend SMTP settings.`
            : 'Invitations were saved, but the backend email service is not configured to send email.',
        );
      }
      setInviteEmails('');
    } catch (inviteFailure: unknown) {
      setInviteError(getErrorMessage(inviteFailure, 'We could not invite those participants. Check the email addresses and try again.'));
    } finally {
      setInviteBusy(false);
    }
  }

  async function acceptInvitation() {
    if (acceptingInvitation) return;
    setAcceptingInvitation(true);
    setError('');
    try {
      await acceptMeetingInvitation(meetingId);
      await loadMeeting();
      setNotice('Invitation accepted. You can join as soon as the host starts the room.');
    } catch (acceptError: unknown) {
      setError(getErrorMessage(acceptError, 'We could not accept this invitation. Try again from your meetings schedule.'));
    } finally {
      setAcceptingInvitation(false);
    }
  }

  async function toggleFullscreen() {
    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen();
      } else {
        await document.documentElement.requestFullscreen();
      }
    } catch {
      setNotice('Fullscreen is not available in this browser.');
    }
  }

  if (authLoading || loading) {
    return <main className={styles.page}><div className={styles.loading}><LoaderCircle size={25} className={styles.spin} /> Loading meeting room</div></main>;
  }

  if (!isBackendAuthenticated) {
    return (
      <main className={styles.page}>
        <section className={styles.stateCard}>
          <ShieldCheck size={30} />
          <h1>Sign in to enter</h1>
          <p>Meeting rooms are available to authorized Ethiopian Startup School members.</p>
          <button
            type="button"
            className={styles.primaryAction}
            onClick={() => window.dispatchEvent(new CustomEvent('open-auth-modal', {
              detail: { returnTo: `/meetings/${meetingId}` },
            }))}
          >Sign in to accept and join</button>
        </section>
      </main>
    );
  }

  if (!meeting) {
    return (
      <main className={styles.page}>
        <section className={styles.stateCard}>
          <CircleHelp size={30} />
          <h1>Room unavailable</h1>
          <p>{error || 'This meeting could not be found or your account does not have access.'}</p>
          <Link className={styles.secondaryAction} href="/meetings"><ArrowLeft size={16} /> Back to meetings</Link>
        </section>
      </main>
    );
  }

  const fullName = user ? `${user.first_name} ${user.last_name}`.trim() || user.username : 'You';
  const liveParticipants = participants.map((participant) => ({
    participant,
    name: participant.name || (participant.identity === localParticipant?.identity ? fullName : participant.identity),
    local: participant.identity === localParticipant?.identity,
    video: getVideoTrack(participant),
    audioTracks: participant.identity === localParticipant?.identity
      ? []
      : Array.from(participant.audioTrackPublications.values())
      .filter((publication: any) => publication.source === Track.Source.Microphone && publication.track && !publication.isMuted)
      .map((publication: any) => publication.track),
  }));
  const statusText = meeting.status === 'ended'
    ? 'Meeting ended'
    : meeting.status === 'cancelled'
      ? 'Meeting cancelled'
      : roomPhase === 'connected'
        ? 'Live · In room'
        : roomPhase === 'reconnecting'
          ? 'Reconnecting'
          : meeting.status === 'live'
            ? 'Live now'
            : 'Waiting for host';

  return (
    <main className={styles.page}>
      <div className={styles.roomShell}>
        <header className={styles.topbar}>
          <div className={styles.heading}>
            <Link href="/meetings" className={styles.backLink} aria-label="Back to meetings"><ArrowLeft size={18} /></Link>
            <div className={styles.titleBlock}>
              <div className={styles.statusLine}>
                <span className={`${styles.statusDot} ${isLive ? styles.statusLive : ''}`} />
                <span>{statusText}</span>
                {isLive && <span className={styles.duration}><Clock3 size={13} /> {formatElapsed(duration)}</span>}
              </div>
              <h1>{meeting.title}</h1>
              <p>{meeting.kind.charAt(0).toUpperCase() + meeting.kind.slice(1)}{meeting.course_title ? ` · ${meeting.course_title}` : ''}</p>
            </div>
          </div>
          <div className={styles.topActions}>
            <span className={styles.secureBadge}><ShieldCheck size={15} /> Private room</span>
            <button type="button" className={styles.iconButton} onClick={() => void toggleFullscreen()} aria-label={fullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}>
              {fullscreen ? <X size={17} /> : <Expand size={17} />}
            </button>
          </div>
        </header>

        {(error || notice || mediaError) && (
          <div className={`${styles.alert} ${error ? styles.alertError : ''}`} role={error || mediaError ? 'alert' : 'status'}>
            <span>{error || mediaError || notice}</span>
            {error && <button type="button" onClick={() => setError('')} aria-label="Dismiss error"><X size={16} /></button>}
            {!error && <button type="button" onClick={() => { setNotice(''); setMediaError(''); }} aria-label="Dismiss message"><X size={16} /></button>}
          </div>
        )}

        <div className={styles.roomLayout}>
          <section className={styles.stageColumn} aria-label="Meeting video">
            <div className={`${styles.sessionContext} ${styles[`session_${meeting.kind}`]}`}>
              <span className={styles.sessionContextIcon}>
                {meeting.kind === 'classroom' ? <BookOpen size={19} /> : meeting.kind === 'consultation' ? <Headphones size={19} /> : <Users size={19} />}
              </span>
              <span className={styles.sessionContextCopy}>
                <strong>{meeting.kind === 'classroom' ? 'Live classroom' : meeting.kind === 'consultation' ? 'Mentor consultation' : 'Group discussion'}</strong>
                <small>
                  {meeting.kind === 'classroom'
                    ? (isHost ? 'Your lesson space · Raise a hand to join in' : 'Your lesson space · Raise a hand to contribute')
                    : meeting.kind === 'consultation'
                      ? 'A private space for focused questions and feedback'
                      : 'Share ideas and build on the group conversation'}
                </small>
              </span>
              <span className={styles.sessionKind}>{meeting.kind === 'classroom' ? 'LEARNING SPACE' : meeting.kind === 'consultation' ? '1:1 SESSION' : 'COLLABORATION'}</span>
            </div>
            {meeting.description && <p className={styles.description}>{meeting.description}</p>}
            {meeting.status === 'scheduled' && !isHost && (
              <div className={styles.waitingPanel}>
                <div className={styles.waitingGlyph}><Clock3 size={25} /></div>
                <h2>Waiting for the host</h2>
                <p>The host will open this room when the session is ready. This page will update automatically.</p>
                <span>Scheduled for {new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(meeting.scheduled_start))}</span>
                {hasPendingInvitation && (
                  <button type="button" className={styles.primaryAction} onClick={() => void acceptInvitation()} disabled={acceptingInvitation}>
                    {acceptingInvitation ? <LoaderCircle size={17} className={styles.spin} /> : <Check size={17} />}
                    Accept invitation
                  </button>
                )}
              </div>
            )}
            {['ended', 'cancelled'].includes(meeting.status) && (
              <div className={styles.waitingPanel}>
                <div className={styles.waitingGlyph}><PhoneOff size={25} /></div>
                <h2>{meeting.status === 'cancelled' ? 'This meeting was cancelled' : 'This meeting has ended'}</h2>
                <p>Thanks for being part of the session.</p>
                <Link className={styles.secondaryAction} href="/meetings"><ArrowLeft size={16} /> Return to meetings</Link>
              </div>
            )}
            {meeting.status === 'live' && roomPhase !== 'connected' && roomPhase !== 'reconnecting' && (
              <div className={styles.waitingPanel}>
                <div className={styles.waitingGlyph}>{roomPhase === 'connecting' ? <LoaderCircle size={25} className={styles.spin} /> : <Video size={25} />}</div>
                <h2>{roomPhase === 'connecting' ? 'Joining the room' : roomPhase === 'disconnected' ? 'Connection closed' : 'The room is live'}</h2>
                <p>{roomPhase === 'disconnected' ? 'Your connection ended. Rejoin to continue.' : 'Join with your microphone and camera off. You can turn them on once you are inside.'}</p>
                {hasPendingInvitation && (
                  <button type="button" className={styles.primaryAction} onClick={() => void acceptInvitation()} disabled={acceptingInvitation}>
                    {acceptingInvitation ? <LoaderCircle size={17} className={styles.spin} /> : <Check size={17} />}
                    Accept invitation
                  </button>
                )}
                {(roomPhase === 'idle' || roomPhase === 'disconnected') && (
                  <div className={styles.waitingActions}>
                    <button type="button" className={styles.primaryAction} onClick={() => void connectToRoom()} disabled={actionBusy}>
                      {actionBusy ? <LoaderCircle size={17} className={styles.spin} /> : <Video size={17} />} Join room
                    </button>
                    {isHost && (
                      <button type="button" className={styles.endButton} onClick={() => void leaveRoom(true)} disabled={actionBusy}>
                        <PhoneOff size={16} /> End meeting
                      </button>
                    )}
                  </div>
                )}
              </div>
            )}
            {meeting.status === 'scheduled' && isHost && (
              <div className={styles.waitingPanel}>
                <div className={styles.waitingGlyph}><Video size={25} /></div>
                <h2>Start when you’re ready</h2>
                <p>Starting opens the room for invited participants. You’ll join as the host.</p>
                <button type="button" className={styles.primaryAction} onClick={() => void connectToRoom(true)} disabled={actionBusy}>
                  {actionBusy ? <LoaderCircle size={17} className={styles.spin} /> : <Video size={17} />} Start session
                </button>
              </div>
            )}
            {room && roomPhase !== 'ended' && (
              <>
                <div className={styles.stageToolbar}>
                  <span><span className={styles.connectedDot} /> {phaseLabel}</span>
                  <span><Users size={15} /> {participants.length} in room</span>
                </div>
                <div className={styles.videoGrid} data-participants={participants.length}>
                  {liveParticipants.map(({ participant, name, local, video, audioTracks }) => (
                    <article
                      className={`${styles.participantTile} ${activeSpeakers.includes(participant.identity) ? styles.speaking : ''} ${video?.source === Track.Source.ScreenShare ? styles.screenTile : ''}`}
                      key={participant.identity}
                    >
                      <VideoSurface track={video} name={name} local={local} large={video?.source === Track.Source.ScreenShare} />
                      {audioTracks.map((audioTrack: any) => <AudioOutput key={audioTrack.sid} track={audioTrack} />)}
                      <span className={styles.participantState}>
                        {raisedHands[participant.identity] && <span className={styles.handTag}>Hand raised</span>}
                        {participant.isMicrophoneEnabled ? <Mic size={13} /> : <MicOff size={13} />}
                      </span>
                    </article>
                  ))}
                  {participants.length === 0 && (
                    <div className={styles.emptyStage}><LoaderCircle size={22} className={styles.spin} /> Waiting for participant media…</div>
                  )}
                </div>
                <div className={styles.controls}>
                  <div className={styles.controlGroup}>
                    <button
                      type="button"
                      className={`${styles.controlButton} ${microphoneOn ? styles.controlOn : styles.controlOff}`}
                      onClick={() => void toggleMicrophone()}
                      disabled={mediaBusy || !mediaSupported.audioVideo}
                      aria-label={microphoneOn ? 'Mute microphone' : 'Unmute microphone'}
                      title={!mediaSupported.audioVideo ? 'Microphone access is not supported in this browser' : microphoneOn ? 'Mute microphone' : 'Unmute microphone'}
                    >{microphoneOn ? <Mic size={19} /> : <MicOff size={19} />}<span>{microphoneOn ? 'Mute' : 'Unmute'}</span></button>
                    <button
                      type="button"
                      className={`${styles.controlButton} ${cameraOn ? styles.controlOn : styles.controlOff}`}
                      onClick={() => void toggleCamera()}
                      disabled={mediaBusy || !mediaSupported.audioVideo}
                      aria-label={cameraOn ? 'Turn camera off' : 'Turn camera on'}
                      title={!mediaSupported.audioVideo ? 'Camera access is not supported in this browser' : cameraOn ? 'Turn camera off' : 'Turn camera on'}
                    >{cameraOn ? <Video size={19} /> : <VideoOff size={19} />}<span>{cameraOn ? 'Stop video' : 'Start video'}</span></button>
                    <button
                      type="button"
                      className={`${styles.controlButton} ${screenShareOn ? styles.controlActive : ''}`}
                      onClick={() => void toggleScreenShare()}
                      disabled={mediaBusy || !mediaSupported.screenShare}
                      aria-label={screenShareOn ? 'Stop screen sharing' : 'Share screen'}
                      title={!mediaSupported.screenShare ? 'Screen sharing is not supported in this browser' : 'Share screen'}
                    ><MonitorUp size={19} /><span>{screenShareOn ? 'Stop share' : 'Share screen'}</span></button>
                    <button
                      type="button"
                      className={`${styles.controlButton} ${handRaised ? styles.controlActive : ''}`}
                      onClick={() => void toggleRaisedHand()}
                      aria-pressed={handRaised}
                      aria-label={handRaised ? 'Lower hand' : 'Raise hand'}
                    ><span className={styles.handIcon} aria-hidden="true">✋</span><span>{handRaised ? 'Lower hand' : 'Raise hand'}</span></button>
                    <button
                      type="button"
                      className={`${styles.controlButton} ${chatOpen ? styles.controlActive : ''}`}
                      onClick={() => { setChatOpen((open) => !open); setUnreadCount(0); }}
                      aria-label={chatOpen ? 'Close chat' : 'Open chat'}
                    ><MessageCircle size={19} /><span>Chat{unreadCount > 0 ? ` · ${unreadCount}` : ''}</span></button>
                  </div>
                  <div className={styles.exitGroup}>
                    {isHost ? (
                      <button type="button" className={styles.endButton} onClick={() => void leaveRoom(true)} disabled={actionBusy}>
                        {actionBusy ? <LoaderCircle size={17} className={styles.spin} /> : <PhoneOff size={17} />} End meeting
                      </button>
                    ) : (
                      <button type="button" className={styles.leaveButton} onClick={() => void leaveRoom()} disabled={actionBusy}>
                        {actionBusy ? <LoaderCircle size={17} className={styles.spin} /> : <PhoneOff size={17} />} Leave
                      </button>
                    )}
                  </div>
                </div>
                {(!mediaSupported.audioVideo || !mediaSupported.screenShare) && (
                  <p className={styles.deviceHint}>
                    Some media controls are unavailable. Use a current browser over HTTPS or localhost.
                  </p>
                )}
              </>
            )}
          </section>

          <aside className={styles.sidebar}>
            <div className={styles.sidebarHeader}>
              <div>
                <p className={styles.eyebrow}>{inviteOpen ? 'HOST TOOLS' : chatOpen ? 'ROOM CHAT' : 'IN THIS SESSION'}</p>
                <h2>{inviteOpen ? 'Invite people' : chatOpen ? 'Messages' : `People${room ? ` · ${participants.length}` : ''}`}</h2>
              </div>
              <div className={styles.sidebarHeaderActions}>
                {isHost && (
                  <button
                    type="button"
                    className={`${styles.iconButton} ${inviteOpen ? styles.controlActive : ''}`}
                    onClick={() => { setInviteOpen((open) => !open); setChatOpen(false); setInviteError(''); }}
                    aria-label={inviteOpen ? 'Close invitations' : 'Invite participants'}
                    title="Invite participants by email"
                  ><UserPlus size={17} /><span className={styles.sidebarActionLabel}>Invite</span></button>
                )}
                {chatOpen || inviteOpen ? (
                  <button
                    type="button"
                    className={styles.iconButton}
                    onClick={() => { setChatOpen(false); setInviteOpen(false); }}
                    aria-label="Show participants"
                  ><Users size={17} /><span className={styles.sidebarActionLabel}>People</span></button>
                ) : (
                  <button type="button" className={styles.iconButton} onClick={() => { setChatOpen(true); setUnreadCount(0); }} aria-label="Open room chat">
                    <MessageCircle size={17} /><span className={styles.sidebarActionLabel}>Chat</span>{unreadCount > 0 && <span className={styles.unreadDot}>{unreadCount}</span>}
                  </button>
                )}
              </div>
            </div>
            {inviteOpen ? (
              <div className={styles.invitePanel}>
                <p>Invite up to 50 people by account email. They must accept the invitation before joining.</p>
                <form onSubmit={(event) => void sendInvitations(event)}>
                  <label className={styles.srOnly} htmlFor="meeting-invite-emails">Participant email addresses</label>
                  <textarea
                    id="meeting-invite-emails"
                    value={inviteEmails}
                    onChange={(event) => setInviteEmails(event.target.value)}
                    rows={4}
                    maxLength={4000}
                    placeholder="learner@example.com, mentor@example.com"
                    disabled={inviteBusy}
                  />
                  <button type="submit" className={styles.primaryAction} disabled={inviteBusy || !inviteEmails.trim()}>
                    {inviteBusy ? <LoaderCircle size={16} className={styles.spin} /> : <UserPlus size={16} />}
                    Send invitations
                  </button>
                </form>
                {inviteError && <p className={styles.inviteError} role="alert">{inviteError}</p>}
                {inviteNotice && <p className={styles.inviteNotice} role="status">{inviteNotice}</p>}
              </div>
            ) : chatOpen ? (
              <div className={styles.chatPanel}>
                <div className={styles.messageList} aria-live="polite">
                  {messages.length === 0 ? (
                    <div className={styles.chatEmpty}><MessageCircle size={21} /><p>Say hello to everyone in the room.</p></div>
                  ) : messages.map((message) => (
                    <div className={`${styles.message} ${message.mine ? styles.ownMessage : ''}`} key={message.id}>
                      <div className={styles.messageMeta}><strong>{message.name}</strong><time>{message.time}</time></div>
                      <p>{message.text}</p>
                    </div>
                  ))}
                </div>
                <form className={styles.chatForm} onSubmit={(event) => void sendChat(event)}>
                  <label className={styles.srOnly} htmlFor="meeting-message">Write a message</label>
                  <input id="meeting-message" value={chatDraft} onChange={(event) => setChatDraft(event.target.value)} maxLength={1500} placeholder="Write a message…" disabled={!room} />
                  <button type="submit" disabled={!room || !chatDraft.trim()} aria-label="Send message"><Send size={17} /></button>
                </form>
                {!room && <p className={styles.chatHint}>Join the room to send a message.</p>}
              </div>
            ) : (
              <div className={styles.roster}>
                {room ? liveParticipants.map(({ participant, name, local }) => (
                  <div className={styles.rosterPerson} key={participant.identity}>
                    <span className={styles.rosterAvatar}>{initials(name)}</span>
                    <span className={styles.rosterName}>{name}{local && <small>You</small>}</span>
                    {raisedHands[participant.identity] && <span className={styles.rosterHand} title="Hand raised">✋</span>}
                    <span className={styles.rosterMic} title={participant.isMicrophoneEnabled ? 'Microphone on' : 'Microphone off'}>
                      {participant.isMicrophoneEnabled ? <Mic size={14} /> : <MicOff size={14} />}
                    </span>
                  </div>
                )) : (
                  <div className={styles.rosterEmpty}>
                    <Users size={21} />
                    <p>Participants will appear here after you join.</p>
                  </div>
                )}
              </div>
            )}
            <div className={styles.sidebarFooter}>
              <span><Wifi size={14} /> {phaseLabel}</span>
              <span>Authorized participants</span>
            </div>
          </aside>
        </div>
        <footer className={styles.roomFooter}>
          <span><ShieldCheck size={14} /> Meeting access is managed by your course host.</span>
          <span>{roomPhase === 'reconnecting' ? <><WifiOff size={14} /> Trying to reconnect</> : <><Check size={14} /> {room ? 'Connected securely' : 'Private meeting'}</>}</span>
        </footer>
      </div>
    </main>
  );
}
