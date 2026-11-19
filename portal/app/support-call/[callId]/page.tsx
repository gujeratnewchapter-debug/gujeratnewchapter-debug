'use client';

import Link from 'next/link';
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ArrowLeft,
  Camera,
  CameraOff,
  CircleHelp,
  Headphones,
  LoaderCircle,
  Mic,
  MicOff,
  PhoneOff,
  ShieldCheck,
  Video,
  Volume2,
  Wifi,
  WifiOff,
} from 'lucide-react';
import { Room, RoomEvent, Track, VideoPresets } from 'livekit-client';
import { isSuperAdminUser, useAuth } from '@/lib/auth-context';
import { enableSupportCallAudio, startSupportCallRingback } from '@/lib/support-call-audio';
import {
  getAdminSupportCall,
  getAdminSessionCall,
  getAdminSessionCallToken,
  getAdminSupportCallToken,
  endAdminSessionCall,
  getSupportCallError,
  getSupportCallStatus,
  getSupportCallToken,
  getStudentSupportCall,
  getStudentSupportCallToken,
  SupportCallState,
  takeSupportCallAction,
} from '@/lib/support-calls';
import styles from './page.module.css';

type RoomPhase = 'waiting' | 'connecting' | 'connected' | 'reconnecting' | 'disconnected' | 'left' | 'ended';

function initials(name: string) {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join('').toUpperCase() || '?';
}

function formatDuration(seconds: number) {
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(remainder).padStart(2, '0')}`;
}

function errorText(error: unknown, fallback: string) {
  const name = (error as { name?: string })?.name;
  if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
    return 'Device access was denied. Allow microphone or camera permissions in your browser settings, then try again.';
  }
  if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
    return 'No matching camera or microphone was found. Connect a device and try again.';
  }
  if (name === 'NotReadableError' || name === 'TrackStartError') {
    return 'A device could not be opened. It may be in use by another application.';
  }
  if (name === 'SecurityError') return 'Camera and microphone access requires HTTPS or localhost.';
  return getSupportCallError(error, fallback);
}

function VideoSurface({ track, label, audio = false, mirrored = false }: { track: any; label: string; audio?: boolean; mirrored?: boolean }) {
  const elementRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!elementRef.current || !track) return;
    const element = track.attach();
    if (audio) {
      element.autoplay = true;
      element.setAttribute('aria-label', label);
      element.className = styles.audioOutput;
    } else {
      element.autoplay = true;
      element.playsInline = true;
      element.className = mirrored
        ? `${styles.videoElement} ${styles.localVideoElement}`
        : styles.videoElement;
    }
    elementRef.current.appendChild(element);
    return () => {
      track.detach(element);
      element.remove();
    };
  }, [audio, label, mirrored, track]);

  return <div ref={elementRef} className={audio ? styles.audioMount : styles.videoMount} />;
}

export default function SupportCallRoomPage({ params }: { params: { callId: string } }) {
  const callId = params.callId;
  const { user, isLoading: authLoading } = useAuth();
  const [modeReady, setModeReady] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const [isStudentRecipient, setIsStudentRecipient] = useState(false);
  const [capability, setCapability] = useState('');
  const [adminSessionCapability, setAdminSessionCapability] = useState('');
  const [call, setCall] = useState<SupportCallState | null>(null);
  const [phase, setPhase] = useState<RoomPhase>('waiting');
  const [loading, setLoading] = useState(true);
  const [joining, setJoining] = useState(false);
  const [ending, setEnding] = useState(false);
  const [error, setError] = useState('');
  const [micEnabled, setMicEnabled] = useState(false);
  const [cameraEnabled, setCameraEnabled] = useState(false);
  const [audioPlaybackBlocked, setAudioPlaybackBlocked] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [, setMediaRevision] = useState(0);
  const [mediaNotice, setMediaNotice] = useState('');
  const [ringbackEnabled, setRingbackEnabled] = useState(false);
  const [ringbackUnavailable, setRingbackUnavailable] = useState(false);
  const roomRef = useRef<Room | null>(null);
  const manualLeaveRef = useRef(false);
  const phaseRef = useRef<RoomPhase>(phase);
  const autoJoinStartedRef = useRef(false);

  useEffect(() => { phaseRef.current = phase; }, [phase]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const adminTicket = new URLSearchParams(window.location.hash.slice(1)).get('admin_ticket') || '';
    const storedAdminSession = window.sessionStorage.getItem(`ess-support-admin:${callId}`) || '';
    const adminMode = params.get('admin') === '1' || Boolean(adminTicket || storedAdminSession);
    const studentMode = params.get('student') === '1';
    setIsAdmin(adminMode);
    setIsStudentRecipient(studentMode);
    if (adminTicket) {
      window.sessionStorage.setItem(`ess-support-admin:${callId}`, adminTicket);
      setAdminSessionCapability(adminTicket);
      window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}`);
    } else if (storedAdminSession) {
      setAdminSessionCapability(storedAdminSession);
    }
    if (!adminMode) {
      setCapability(window.sessionStorage.getItem(`ess-support-call:${callId}`) || '');
    }
    setModeReady(true);
  }, [callId]);

  const refreshCall = useCallback(async () => {
    try {
      const { data } = isAdmin
        ? adminSessionCapability
          ? await getAdminSessionCall(callId, adminSessionCapability)
          : await getAdminSupportCall(callId)
        : isStudentRecipient
          ? await getStudentSupportCall(callId)
          : await getSupportCallStatus(callId, capability);
      setCall(data);
      setError('');
      if (data.status === 'ended' || data.status === 'rejected' || data.status === 'expired') {
        manualLeaveRef.current = true;
        roomRef.current?.disconnect();
        roomRef.current = null;
        if (isAdmin) {
          window.sessionStorage.removeItem(`ess-support-admin:${callId}`);
        } else {
          window.sessionStorage.removeItem(`ess-support-call:${callId}`);
        }
        setPhase('ended');
      }
    } catch (requestError) {
      setError(getSupportCallError(
        requestError,
        'We could not check this call. Please check your connection and retry.',
      ));
    } finally {
      setLoading(false);
    }
  }, [adminSessionCapability, callId, capability, isAdmin, isStudentRecipient]);

  useEffect(() => {
    if (!modeReady) return;
    if (!isAdmin && !isStudentRecipient && !capability) {
      setLoading(false);
      setError('This private call link is not available in this browser session. Please submit a new request.');
      return;
    }
    if ((isAdmin && !adminSessionCapability || isStudentRecipient) && authLoading) return;
    if (isAdmin && !adminSessionCapability && !isSuperAdminUser(user)) {
      setLoading(false);
      setError('Administrator access is required to join this support call.');
      return;
    }
    void refreshCall();
    const poll = window.setInterval(() => {
      if (phaseRef.current !== 'ended') void refreshCall();
    }, 8000);
    return () => window.clearInterval(poll);
  }, [adminSessionCapability, authLoading, capability, isAdmin, isStudentRecipient, modeReady, refreshCall, user]);

  useEffect(() => {
    if (phase !== 'connected' && phase !== 'reconnecting') return;
    const timer = window.setInterval(() => setElapsed((value) => value + 1), 1000);
    return () => window.clearInterval(timer);
  }, [phase]);

  useEffect(() => {
    if (call?.status !== 'pending') return;
    const stopRingback = startSupportCallRingback();
    if (!stopRingback && !ringbackEnabled) setRingbackUnavailable(true);
    return stopRingback ?? undefined;
  }, [call?.status, ringbackEnabled]);

  useEffect(() => () => {
    roomRef.current?.disconnect();
  }, []);

  const participants = (() => {
    const room = roomRef.current;
    if (!room) return [];
    return [room.localParticipant, ...Array.from(room.remoteParticipants.values())].map((participant: any) => {
      const isLocal = participant === room.localParticipant;
      const videoTracks = (Array.from(participant.videoTrackPublications.values()) as any[])
        .filter((publication) => publication.track && publication.track.kind === Track.Kind.Video)
        .map((publication) => publication.track);
      const audioTracks = isLocal ? [] : (Array.from(participant.audioTrackPublications.values()) as any[])
        .filter((publication) => publication.track && publication.track.kind === Track.Kind.Audio)
        .map((publication) => publication.track);
      const label = isLocal ? 'You' : isAdmin ? (call?.display_name || 'Caller') : 'ESS Support Administrator';
      return { id: participant.identity, label, isLocal, videoTracks, audioTracks };
    });
  })();

  const connectToCall = useCallback(async () => {
    if (!call || call.status !== 'accepted') return;
    setJoining(true);
    setError('');
    setMediaNotice('');
    manualLeaveRef.current = false;
    setPhase('connecting');
    let room: Room | null = null;
    try {
      const { data: credentials } = isAdmin
        ? adminSessionCapability
          ? await getAdminSessionCallToken(callId, adminSessionCapability)
          : await getAdminSupportCallToken(callId)
        : isStudentRecipient
          ? await getStudentSupportCallToken(callId)
          : await getSupportCallToken(callId, capability);
      room = new Room({
        adaptiveStream: true,
        dynacast: true,
        videoCaptureDefaults: {
          resolution: VideoPresets.h720.resolution,
          facingMode: 'user',
        },
        publishDefaults: {
          videoEncoding: VideoPresets.h720.encoding,
        },
      });
      roomRef.current = room;
      const refreshTracks = () => setMediaRevision((value) => value + 1);
      const refreshAudioPlayback = () => setAudioPlaybackBlocked(!room?.canPlaybackAudio);
      room.on(RoomEvent.TrackSubscribed, refreshTracks);
      room.on(RoomEvent.TrackUnsubscribed, refreshTracks);
      room.on(RoomEvent.LocalTrackPublished, refreshTracks);
      room.on(RoomEvent.LocalTrackUnpublished, refreshTracks);
      room.on(RoomEvent.ParticipantConnected, refreshTracks);
      room.on(RoomEvent.ParticipantDisconnected, refreshTracks);
      room.on(RoomEvent.AudioPlaybackStatusChanged, refreshAudioPlayback);
      room.on(RoomEvent.Reconnecting, () => setPhase('reconnecting'));
      room.on(RoomEvent.Reconnected, () => setPhase('connected'));
      room.on(RoomEvent.Disconnected, () => {
        setMediaRevision((value) => value + 1);
        if (!manualLeaveRef.current && phaseRef.current !== 'ended') setPhase('disconnected');
      });
      await room.connect(credentials.url, credentials.token);
      setPhase('connected');
      setMediaRevision((value) => value + 1);
      setElapsed(0);
      try {
        await room.startAudio();
        setAudioPlaybackBlocked(false);
      } catch {
        setAudioPlaybackBlocked(true);
      }
      try {
        await room.localParticipant.setMicrophoneEnabled(true);
        setMicEnabled(true);
      } catch {
        setMicEnabled(false);
        setMediaNotice('You are connected, but your microphone is unavailable. Check its permission or device.');
      }
      if (call.mode === 'video') {
        try {
          await room.localParticipant.setCameraEnabled(true);
          setCameraEnabled(true);
        } catch {
          setCameraEnabled(false);
          setMediaNotice((current) => current
            ? `${current} Camera permission is also unavailable.`
            : 'You are connected, but your camera is unavailable. Check its permission or device.');
        }
      }
    } catch (connectionError) {
      room?.disconnect();
      roomRef.current = null;
      setPhase('waiting');
      setError(errorText(connectionError, 'Could not join this call. Please retry in a moment.'));
    } finally {
      setJoining(false);
    }
  }, [adminSessionCapability, call, callId, capability, isAdmin, isStudentRecipient]);

  useEffect(() => {
    const shouldAutoJoin = new URLSearchParams(window.location.search).get('autojoin') === '1';
    if (
      !shouldAutoJoin
      || !call
      || call.status !== 'accepted'
      || phase !== 'waiting'
      || autoJoinStartedRef.current
    ) return;
    autoJoinStartedRef.current = true;
    void connectToCall();
  }, [call, connectToCall, phase]);

  async function toggleMicrophone() {
    const room = roomRef.current;
    if (!room) return;
    try {
      await room.localParticipant.setMicrophoneEnabled(!micEnabled);
      setMicEnabled(!micEnabled);
    } catch (deviceError) {
      setMediaNotice(errorText(deviceError, 'The microphone could not be changed.'));
    }
  }

  async function toggleCamera() {
    const room = roomRef.current;
    if (!room) return;
    try {
      await room.localParticipant.setCameraEnabled(!cameraEnabled);
      setCameraEnabled(!cameraEnabled);
    } catch (deviceError) {
      setMediaNotice(errorText(deviceError, 'The camera could not be changed.'));
    }
  }

  async function enableCallAudio() {
    const room = roomRef.current;
    if (!room) return;
    try {
      await room.startAudio();
      setAudioPlaybackBlocked(false);
    } catch (audioError) {
      setAudioPlaybackBlocked(true);
      setMediaNotice(errorText(audioError, 'Call audio could not be enabled. Check your browser audio settings.'));
    }
  }

  async function enableRingback() {
    try {
      const enabled = await enableSupportCallAudio();
      if (!enabled) {
        setRingbackUnavailable(true);
        return;
      }
      setRingbackEnabled(true);
      setRingbackUnavailable(false);
    } catch (audioError) {
      setRingbackUnavailable(true);
      setError(errorText(audioError, 'Calling tone could not be enabled. Check your browser audio settings.'));
    }
  }

  function leaveCall() {
    manualLeaveRef.current = true;
    roomRef.current?.disconnect();
    roomRef.current = null;
    setMicEnabled(false);
    setCameraEnabled(false);
    setAudioPlaybackBlocked(false);
    setPhase('left');
  }

  async function endCallForEveryone() {
    setEnding(true);
    setError('');
    try {
      if (adminSessionCapability) {
        await endAdminSessionCall(callId, adminSessionCapability);
      } else {
        await takeSupportCallAction(callId, 'end');
      }
      manualLeaveRef.current = true;
      roomRef.current?.disconnect();
      roomRef.current = null;
      setCall((current) => current ? { ...current, status: 'ended' } : current);
      setPhase('ended');
    } catch (actionError) {
      setError(getSupportCallError(actionError, 'The call could not be ended. Please try again.'));
    } finally {
      setEnding(false);
    }
  }

  const waiting = call?.status === 'pending';
  const declined = call?.status === 'rejected';
  const expired = call?.status === 'expired';
  const ended = call?.status === 'ended' || phase === 'ended';
  const connected = phase === 'connected' || phase === 'reconnecting';

  if (isAdmin && !adminSessionCapability && !authLoading && !isSuperAdminUser(user)) {
    return (
      <main className={styles.statePage}>
        <div className={styles.stateIcon}><ShieldCheck size={23} /></div>
        <h1>Administrator access required</h1>
        <p>Only an ESS administrator can join this support call.</p>
        <Link href="/">Return to ESS</Link>
      </main>
    );
  }

  if (!modeReady || loading || (isAdmin && !adminSessionCapability && authLoading) || (isStudentRecipient && authLoading)) {
    return <main className={styles.statePage}><LoaderCircle className={styles.spinner} /><p>Checking your support call…</p></main>;
  }

  if (error && !call && !isAdmin) {
    return (
      <main className={styles.statePage}>
        <div className={styles.stateIcon}><CircleHelp size={23} /></div>
        <h1>We can’t open this call</h1>
        <p role="alert">{error}</p>
        <Link href="/support-call">Request a new support call</Link>
      </main>
    );
  }

  if (waiting || !call || declined || expired || ended || phase === 'left' || phase === 'disconnected') {
    const title = declined ? 'This request was declined'
      : expired ? 'This request has expired'
        : ended ? 'This call has ended'
          : phase === 'left' ? 'You left the call'
            : phase === 'disconnected' ? 'Connection interrupted'
              : 'Your request is with the support team';
    const description = declined ? 'Your request could not be accepted right now. You can try again later.'
      : expired ? 'No administrator accepted this request in time. Please request another call when you’re ready.'
        : ended ? 'The administrator has ended this support call.'
          : phase === 'left' ? 'You have left the room. Leaving does not end the call for the administrator.'
            : phase === 'disconnected' ? 'Your connection dropped. You can rejoin while the administrator is still available.'
              : 'An administrator will join when available. This page checks for updates automatically.';

    return (
      <main className={styles.waitPage}>
        <div className={styles.waitCard}>
          <div className={styles.waitIcon}>{ended || declined || expired ? <Headphones size={25} /> : <LoaderCircle size={25} className={styles.spinner} />}</div>
          <div className={styles.eyebrow}>ESS SUPPORT DESK <span>•</span> {call?.mode === 'video' ? 'VIDEO CALL' : 'VOICE CALL'}</div>
          <h1>{title}</h1>
          <p>{description}</p>
          {waiting && (
            <div className={styles.queueNotice}>
              <span className={styles.pulse} />
              <span>Calling ESS support<small>Your calling tone repeats until an administrator responds. Keep this page open.</small></span>
            </div>
          )}
          {error && <p className={styles.inlineError} role="alert">{error}</p>}
          {waiting && ringbackUnavailable && (
            <button type="button" className={styles.primaryButton} onClick={() => void enableRingback()}>
              <Volume2 size={16} /> Enable calling tone
            </button>
          )}
          {call?.status === 'accepted' && !ended && phase !== 'connecting' && phase !== 'connected' && phase !== 'reconnecting' && (
            <button type="button" className={styles.primaryButton} onClick={() => void connectToCall()} disabled={joining}>
              {joining
                ? <><LoaderCircle size={16} className={styles.spinner} /> Connecting…</>
                : phase === 'left' || phase === 'disconnected' ? 'Rejoin call' : 'Join support call'}
            </button>
          )}
          <Link className={styles.homeLink} href={isAdmin ? '/admin/support-calls' : '/'}>{isAdmin ? 'Back to support queue' : 'Return to ESS home'}</Link>
        </div>
      </main>
    );
  }

  return (
    <main className={styles.callPage}>
      <header className={styles.callHeader}>
        <div className={styles.brand}>
          <Link href={isAdmin ? '/admin/support-calls' : '/'} aria-label="Leave support call page"><ArrowLeft size={17} /></Link>
          <span className={styles.brandMark}><Headphones size={18} /></span>
          <span><strong>ESS Support</strong><small>Direct voice &amp; video</small></span>
        </div>
        <div className={styles.callStatus}>
          <span className={connected ? styles.statusLive : styles.statusWaiting} />
          {phase === 'reconnecting' ? 'Reconnecting' : connected ? 'Connected' : phase === 'connecting' ? 'Connecting' : 'Ready to join'}
        </div>
        <div className={styles.duration}>{formatDuration(elapsed)}</div>
      </header>

      <section className={styles.callContent} aria-label="Support call room">
        <div className={styles.callContext}>
          <div>
            <span className={styles.eyebrow}>{call.mode === 'video' ? 'VIDEO SUPPORT' : 'VOICE SUPPORT'} <span>•</span> PRIVATE CALL</span>
            <h1>{isAdmin ? `Helping ${call.display_name}` : 'You’re speaking with ESS support'}</h1>
            <p>{connected ? 'Your call is active. Use the controls below to manage your microphone and camera.' : 'The call is accepted. Connect when you are ready.'}</p>
          </div>
          <div className={styles.secureTag}><ShieldCheck size={15} /> Private connection</div>
        </div>

        <div className={`${styles.stage} ${participants.length > 1 ? styles.stageGrid : ''}`}>
          {participants.length > 0 ? participants.map((participant) => (
            <article key={participant.id} className={styles.participantTile}>
              {participant.videoTracks.length > 0
                ? participant.videoTracks.map((track: any, index: number) => (
                  <VideoSurface key={`${participant.id}:${index}`} track={track} label={`${participant.label} video`} mirrored={participant.isLocal} />
                ))
                : <div className={styles.avatarFallback}><span>{initials(participant.label)}</span></div>}
              {participant.audioTracks.map((track: any, index: number) => (
                <VideoSurface key={`${participant.id}:audio:${index}`} track={track} label={`${participant.label} audio`} audio />
              ))}
              <div className={styles.tileLabel}><span className={participant.isLocal ? styles.localIndicator : styles.remoteIndicator} />{participant.label}{participant.isLocal ? ' · You' : ''}</div>
              {participant.isLocal && !micEnabled && <span className={styles.mutedBadge}><MicOff size={12} /> Muted</span>}
            </article>
          )) : (
            <div className={styles.readyStage}>
              <div className={styles.readyHalo}><Headphones size={30} /></div>
              <strong>{phase === 'connecting' ? 'Connecting securely…' : 'Your support call is ready'}</strong>
              <span>{call.mode === 'video' ? 'Your microphone and camera turn on only after you join.' : 'Your microphone turns on only after you join.'}</span>
              {!connected && (
                <button type="button" className={styles.joinButton} onClick={() => void connectToCall()} disabled={joining || call.status !== 'accepted'}>
                  {joining ? <><LoaderCircle size={16} className={styles.spinner} /> Connecting…</> : 'Join call'}
                </button>
              )}
            </div>
          )}
        </div>

        {mediaNotice && <p className={styles.mediaNotice} role="status">{mediaNotice}</p>}
        {audioPlaybackBlocked && connected && !mediaNotice && (
          <p className={styles.mediaNotice} role="status">
            Your browser blocked incoming call audio. Tap “Enable audio” to hear the other participant.
          </p>
        )}
        {error && <p className={styles.inlineError} role="alert">{error}</p>}
        <div className={styles.controls}>
          <div className={styles.mediaControls}>
            {audioPlaybackBlocked && connected && (
              <button type="button" className={styles.controlButton} onClick={() => void enableCallAudio()}>
                <Volume2 size={18} />
                <span>Enable audio</span>
              </button>
            )}
            <button type="button" className={`${styles.controlButton} ${!micEnabled ? styles.controlOff : ''}`} onClick={() => void toggleMicrophone()} disabled={!connected} aria-label={micEnabled ? 'Mute microphone' : 'Unmute microphone'}>
              {micEnabled ? <Mic size={18} /> : <MicOff size={18} />}
              <span>{micEnabled ? 'Mute' : 'Unmute'}</span>
            </button>
            {call.mode === 'video' && (
              <button type="button" className={`${styles.controlButton} ${!cameraEnabled ? styles.controlOff : ''}`} onClick={() => void toggleCamera()} disabled={!connected} aria-label={cameraEnabled ? 'Turn camera off' : 'Turn camera on'}>
                {cameraEnabled ? <Camera size={18} /> : <CameraOff size={18} />}
                <span>{cameraEnabled ? 'Camera on' : 'Camera off'}</span>
              </button>
            )}
          </div>
          <div className={styles.connectionInfo}>{connected ? <><Wifi size={14} /> Secure live connection</> : <><WifiOff size={14} /> Not connected yet</>}</div>
          <div className={styles.endControls}>
            {connected && (
              <button type="button" className={styles.leaveButton} onClick={leaveCall}>
                <PhoneOff size={17} /> Leave call
              </button>
            )}
            {isAdmin && call.status === 'accepted' && (
              <button type="button" className={styles.endAllButton} onClick={() => void endCallForEveryone()} disabled={ending}>
                {ending ? <LoaderCircle size={16} className={styles.spinner} /> : <PhoneOff size={16} />}
                End for everyone
              </button>
            )}
          </div>
        </div>
        <p className={styles.disclaimer}><Video size={13} /> Voice/video, mute, camera, leave and administrator end controls only. Calls are not recorded.</p>
      </section>
    </main>
  );
}
