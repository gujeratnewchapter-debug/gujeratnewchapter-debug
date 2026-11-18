'use client';

import Link from 'next/link';
import { FormEvent, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Headphones, LoaderCircle, LockKeyhole, Phone, Video } from 'lucide-react';
import { useAuth } from '@/lib/auth-context';
import { createSupportCall, getSupportCallError, SupportCallMode } from '@/lib/support-calls';
import { enableSupportCallAudio } from '@/lib/support-call-audio';
import styles from './page.module.css';

export default function SupportCallRequestPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [mode, setMode] = useState<SupportCallMode>('audio');
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [question, setQuestion] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const selectedMode = new URLSearchParams(window.location.search).get('mode');
    if (selectedMode === 'video' || selectedMode === 'audio') setMode(selectedMode);
  }, []);

  useEffect(() => {
    if (!user) return;
    setDisplayName([user.first_name, user.last_name].filter(Boolean).join(' ') || user.username || '');
    setEmail(user.email || '');
  }, [user]);

  async function submitRequest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError('');
    const audioReady = enableSupportCallAudio().catch(() => false);
    try {
      const { data } = await createSupportCall({
        display_name: displayName.trim(),
        email: email.trim(),
        question: question.trim(),
        mode,
      });
      await audioReady;
      window.sessionStorage.setItem(`ess-support-call:${data.call_id}`, data.capability);
      router.push(`/support-call/${data.call_id}`);
    } catch (requestError) {
      setError(getSupportCallError(
        requestError,
        'We could not send your request right now. Please check your connection and try again.',
      ));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className={styles.page}>
      <div className={styles.topRule} aria-hidden="true" />
      <div className={styles.layout}>
        <aside className={styles.intro}>
          <div className={styles.eyebrow}><Headphones size={15} /> Ethiopian Startup School support</div>
          <h1>Let’s find the right person to help.</h1>
          <p>
            Send a short request and an administrator will join you when available. You’ll stay here while your call is in the queue.
          </p>
          <ul className={styles.promises}>
            <li><span>01</span><div><strong>Private request</strong><small>Your email is only visible to the support team.</small></div></li>
            <li><span>02</span><div><strong>You choose when to join</strong><small>Your camera and microphone are not enabled until you join.</small></div></li>
            <li><span>03</span><div><strong>Simple, direct help</strong><small>Audio and video calls only; no recording or extra meeting features.</small></div></li>
          </ul>
          <Link className={styles.backLink} href="/">← Back to the ESS home page</Link>
        </aside>

        <section className={styles.formPanel} aria-labelledby="request-title">
          <div className={styles.panelHeading}>
            <div className={styles.step}>REQUEST A CALL <span>•</span> ABOUT 1 MINUTE</div>
            <h2 id="request-title">How can we reach you?</h2>
            <p>Share only what the administrator needs to get started.</p>
          </div>
          <form onSubmit={submitRequest} className={styles.form}>
            <fieldset className={styles.modeField}>
              <legend>Choose a call type</legend>
              <div className={styles.modeOptions}>
                <button
                  type="button"
                  className={`${styles.modeOption} ${mode === 'audio' ? styles.modeSelected : ''}`}
                  aria-pressed={mode === 'audio'}
                  onClick={() => setMode('audio')}
                >
                  <Phone size={18} />
                  <span><strong>Voice call</strong><small>Microphone only</small></span>
                  <span className={styles.radioMark} aria-hidden="true" />
                </button>
                <button
                  type="button"
                  className={`${styles.modeOption} ${mode === 'video' ? styles.modeSelected : ''}`}
                  aria-pressed={mode === 'video'}
                  onClick={() => setMode('video')}
                >
                  <Video size={18} />
                  <span><strong>Video call</strong><small>Camera and microphone</small></span>
                  <span className={styles.radioMark} aria-hidden="true" />
                </button>
              </div>
            </fieldset>

            <div className={styles.field}>
              <label htmlFor="support-display-name">Your name</label>
              <input
                id="support-display-name"
                name="display_name"
                autoComplete="name"
                minLength={2}
                maxLength={100}
                required
                value={displayName}
                readOnly={Boolean(user)}
                onChange={(event) => setDisplayName(event.target.value)}
              />
            </div>
            <div className={styles.field}>
              <label htmlFor="support-email">Email address</label>
              <input
                id="support-email"
                name="email"
                type="email"
                autoComplete="email"
                maxLength={254}
                required
                value={email}
                readOnly={Boolean(user)}
                onChange={(event) => setEmail(event.target.value)}
              />
              {user && <small>We’ll use the email saved to your ESS account.</small>}
            </div>
            <div className={styles.field}>
              <label htmlFor="support-question">What would you like help with? <span>Optional</span></label>
              <textarea
                id="support-question"
                name="question"
                rows={3}
                maxLength={500}
                placeholder="A short summary helps us prepare."
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
              />
              <small>{question.length}/500 characters. Please don’t include passwords or sensitive information.</small>
            </div>
            {error && <p className={styles.error} role="alert">{error}</p>}
            <button type="submit" className={styles.submit} disabled={submitting}>
              {submitting ? <><LoaderCircle size={17} className={styles.spinner} /> Sending request…</> : <>Join the support queue <span aria-hidden="true">→</span></>}
            </button>
            <p className={styles.privacy}><LockKeyhole size={14} /> Your call link is private to this browser session.</p>
          </form>
        </section>
      </div>
    </main>
  );
}
