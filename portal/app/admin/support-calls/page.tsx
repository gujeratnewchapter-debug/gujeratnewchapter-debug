'use client';

import Link from 'next/link';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Bell, BellOff, Headphones, LoaderCircle, Phone, RefreshCw, Video } from 'lucide-react';
import { isSuperAdminUser, useAuth } from '@/lib/auth-context';
import {
  getAdminSupportCalls,
  getSupportCallError,
  SupportCallState,
  takeSupportCallAction,
} from '@/lib/support-calls';
import styles from './page.module.css';

function requestTime(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

function playIncomingRingtone(context: AudioContext) {
  const startAt = context.currentTime;
  [0, 0.24].forEach((offset, index) => {
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    const toneStart = startAt + offset;
    oscillator.type = 'sine';
    oscillator.frequency.value = index === 0 ? 660 : 880;
    gain.gain.setValueAtTime(0.0001, toneStart);
    gain.gain.exponentialRampToValueAtTime(0.16, toneStart + 0.025);
    gain.gain.exponentialRampToValueAtTime(0.0001, toneStart + 0.19);
    oscillator.connect(gain);
    gain.connect(context.destination);
    oscillator.start(toneStart);
    oscillator.stop(toneStart + 0.2);
  });
}

export default function AdminSupportCallsPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const isAdmin = isSuperAdminUser(user);
  const [calls, setCalls] = useState<SupportCallState[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
  const [soundEnabled, setSoundEnabled] = useState(false);
  const [soundError, setSoundError] = useState('');
  const audioContextRef = useRef<AudioContext | null>(null);
  const alertedCallIds = useRef(new Set<string>());
  const pending = calls.filter((call) => call.status === 'pending');
  const pendingCount = pending.length;
  const active = calls.filter((call) => call.status === 'accepted');

  const refresh = useCallback(async () => {
    try {
      const { data } = await getAdminSupportCalls();
      setCalls(data);
      setError('');
    } catch (requestError) {
      setError(getSupportCallError(requestError, 'Could not load the support queue. Please try again.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isLoading || !isAdmin) return;
    void refresh();
    const timer = window.setInterval(() => { void refresh(); }, 6000);
    return () => window.clearInterval(timer);
  }, [isAdmin, isLoading, refresh]);

  useEffect(() => {
    pending.forEach((call) => {
      if (alertedCallIds.current.has(call.call_id)) return;
      if (!soundEnabled || !('Notification' in window) || Notification.permission !== 'granted') return;

      alertedCallIds.current.add(call.call_id);
      const notification = new Notification(`Incoming ${call.mode_label || call.mode} call`, {
        body: `${call.display_name}${call.question ? `: ${call.question}` : ''}`,
        tag: `ess-support-call-${call.call_id}`,
        requireInteraction: false,
      });
      notification.onclick = () => {
        window.focus();
        document.getElementById(`support-call-${call.call_id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        notification.close();
      };
    });
  }, [pending, soundEnabled]);

  useEffect(() => {
    const context = audioContextRef.current;
    if (!soundEnabled || pendingCount === 0 || !context || context.state !== 'running') return;

    playIncomingRingtone(context);
    const timer = window.setInterval(() => playIncomingRingtone(context), 2800);
    return () => window.clearInterval(timer);
  }, [soundEnabled, pendingCount]);

  useEffect(() => () => {
    void audioContextRef.current?.close();
    audioContextRef.current = null;
  }, []);

  async function toggleCallSound() {
    setSoundError('');
    if (soundEnabled) {
      setSoundEnabled(false);
      return;
    }

    try {
      const context = audioContextRef.current ?? new AudioContext();
      audioContextRef.current = context;
      const resumeAudio = context.resume();
      const notificationPermission = 'Notification' in window && Notification.permission === 'default'
        ? Notification.requestPermission().catch(() => 'denied' as NotificationPermission)
        : Promise.resolve('Notification' in window ? Notification.permission : 'denied');
      await resumeAudio;
      const permission = await notificationPermission;
      setSoundEnabled(true);
      if (permission === 'denied') {
        setSoundError('Sound is on, but browser notifications are blocked. Allow notifications for this site in your browser settings.');
      }
    } catch {
      setSoundError('Call sound could not be enabled. Check your browser audio settings and try again.');
    }
  }

  async function handleAction(call: SupportCallState, action: 'accept' | 'reject' | 'end') {
    setBusy(`${call.call_id}:${action}`);
    setError('');
    try {
      await takeSupportCallAction(call.call_id, action);
      await refresh();
      if (action === 'accept') {
        router.push(`/support-call/${call.call_id}?admin=1`);
      }
    } catch (requestError) {
      setError(getSupportCallError(requestError, 'That action could not be completed. Refresh the queue and try again.'));
      await refresh();
    } finally {
      setBusy(null);
    }
  }

  if (isLoading) {
    return <main className={styles.state}><LoaderCircle className={styles.spinner} /> Loading administrator access…</main>;
  }

  if (!isAdmin) {
    return (
      <main className={styles.state}>
        <h1>Administrator access required</h1>
        <p>This support queue is available only to ESS administrators.</p>
        <Link href="/">Return to the home page</Link>
      </main>
    );
  }

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <div>
          <div className={styles.eyebrow}><Headphones size={15} /> SUPPORT DESK</div>
          <h1>Support call queue</h1>
          <p>Accept a request to connect directly. Keep this page open to see new callers.</p>
        </div>
        <div className={styles.headerActions}>
          <button type="button" className={soundEnabled ? styles.soundEnabled : styles.refresh} onClick={() => void toggleCallSound()} aria-pressed={soundEnabled}>
            {soundEnabled ? <Bell size={15} /> : <BellOff size={15} />}
            {soundEnabled ? 'Alerts & sound on' : 'Enable alerts & sound'}
          </button>
          <button type="button" className={styles.refresh} onClick={() => void refresh()} disabled={loading}>
            <RefreshCw size={15} className={loading ? styles.spinner : ''} /> Refresh
          </button>
        </div>
      </header>

      <div className={styles.availability}>
        <span className={styles.liveDot} />
        Queue updates every 6 seconds
        <span>•</span>
        {soundEnabled ? 'Incoming call sound enabled' : 'Enable alerts and sound here'}
        <span>•</span>
        Visitors wait up to 10 minutes for an administrator
      </div>

      {error && <div className={styles.error} role="alert">{error}</div>}
      {soundError && <div className={styles.error} role="alert">{soundError}</div>}

      <section aria-labelledby="waiting-title" className={styles.section}>
        <div className={styles.sectionHeading}>
          <div><h2 id="waiting-title">Waiting for help</h2><span>{pending.length} {pending.length === 1 ? 'request' : 'requests'}</span></div>
        </div>
        {loading && calls.length === 0 ? (
          <div className={styles.empty}><LoaderCircle className={styles.spinner} /> Loading queue…</div>
        ) : pending.length === 0 ? (
          <div className={styles.empty}><span className={styles.emptyMark}><Headphones size={21} /></span><strong>No one is waiting</strong><small>New requests will appear here automatically.</small></div>
        ) : (
          <div className={styles.queueList}>
            {pending.map((call) => (
              <article className={styles.callCard} id={`support-call-${call.call_id}`} key={call.call_id}>
                <div className={styles.callIdentity}>
                  <span className={styles.avatar}>{call.display_name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()}</span>
                  <div className={styles.caller}>
                    <strong>{call.display_name}</strong>
                    <a href={`mailto:${call.email}`}>{call.email}</a>
                  </div>
                </div>
                <div className={styles.callMeta}>
                  <span className={styles.mode}>{call.mode === 'video' ? <Video size={15} /> : <Phone size={15} />}{call.mode_label || (call.mode === 'video' ? 'Video call' : 'Voice call')}</span>
                  <span>Requested {requestTime(call.created_at || '')}</span>
                </div>
                {call.question && <p className={styles.question}>{call.question}</p>}
                <div className={styles.actions}>
                  <button type="button" className={styles.reject} onClick={() => void handleAction(call, 'reject')} disabled={busy !== null}>
                    {busy === `${call.call_id}:reject` ? 'Rejecting…' : 'Decline'}
                  </button>
                  <button type="button" className={styles.accept} onClick={() => void handleAction(call, 'accept')} disabled={busy !== null}>
                    {busy === `${call.call_id}:accept` ? <><LoaderCircle size={15} className={styles.spinner} /> Accepting…</> : 'Accept & join'}
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <section aria-labelledby="active-title" className={styles.section}>
        <div className={styles.sectionHeading}>
          <div><h2 id="active-title">Accepted calls</h2><span>{active.length} active</span></div>
        </div>
        {active.length === 0 ? (
          <div className={styles.activeEmpty}>No accepted calls are in progress.</div>
        ) : (
          <div className={styles.activeList}>
            {active.map((call) => (
              <article key={call.call_id} className={styles.activeCall}>
                <div><strong>{call.display_name}</strong><span>{call.mode_label || call.mode} · accepted {call.accepted_at ? requestTime(call.accepted_at) : 'just now'}</span></div>
                <div className={styles.actions}>
                  <button type="button" className={styles.join} onClick={() => router.push(`/support-call/${call.call_id}?admin=1`)}>Join call</button>
                  <button type="button" className={styles.reject} onClick={() => void handleAction(call, 'end')} disabled={busy !== null}>End for everyone</button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <footer className={styles.footer}><Link href="/">← Back to ESS</Link><span>Support calling is available while an administrator is online.</span></footer>
    </main>
  );
}
