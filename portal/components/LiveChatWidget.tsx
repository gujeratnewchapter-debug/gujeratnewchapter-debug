'use client';

import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import axios from 'axios';
import { LifeBuoy, MessageCircle, Minimize2, RefreshCw, Send, X } from 'lucide-react';
import { API_BASE_URL } from '@/lib/api';
import styles from './LiveChatWidget.module.css';

type MessageRole = 'user' | 'assistant';

interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  createdAt: string;
  complete: boolean;
}

interface RetryState {
  question: string;
  userMessageId: string;
  history: Array<{ role: MessageRole; content: string }>;
  detail: string;
}

const STORAGE_KEY = 'ess-support-chat-session-v1';
const MAX_SAVED_MESSAGES = 60;
const MAX_HISTORY_MESSAGES = 12;
const supportChatClient = axios.create({ baseURL: API_BASE_URL, timeout: 95000 });

const STARTER_PROMPTS = [
  'How do I enroll in a course?',
  'Where can I get help from a person?',
  'What can I learn at ESS?',
];

function createMessage(role: MessageRole, content: string, complete: boolean): ChatMessage {
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    role,
    content,
    createdAt: new Date().toISOString(),
    complete,
  };
}

function readSavedMessages(): ChatMessage[] {
  try {
    const saved = window.sessionStorage.getItem(STORAGE_KEY);
    if (!saved) return [];
    const parsed: unknown = JSON.parse(saved);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter((message): message is ChatMessage => (
        message
        && (message.role === 'user' || message.role === 'assistant')
        && typeof message.content === 'string'
        && typeof message.createdAt === 'string'
        && typeof message.id === 'string'
        && typeof message.complete === 'boolean'
        && !Number.isNaN(Date.parse(message.createdAt))
      ))
      .slice(-MAX_SAVED_MESSAGES);
  } catch {
    return [];
  }
}

function saveMessages(messages: ChatMessage[]) {
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-MAX_SAVED_MESSAGES)));
  } catch {
    // The conversation remains usable if browser storage is unavailable.
  }
}

function readableError(error: unknown) {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status;
    if (status === 503) {
      return 'The ESS support assistant is temporarily unavailable or not configured on the server. No reply was generated. Please try again later or contact the ESS team.';
    }
    if (status === 429) {
      return 'You have sent several messages in a short time. Please wait a minute and try again.';
    }
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (!error.response) return 'We could not reach the ESS support service. Check your connection and try again.';
  }
  return 'We could not get a reply just now. Please try again or contact the ESS team.';
}

function getHistory(messages: ChatMessage[]) {
  const history = messages
    .filter((message) => message.complete)
    .slice(-MAX_HISTORY_MESSAGES)
    .map(({ role, content }) => ({ role, content: content.slice(0, 2000) }));

  while (
    history.length > 2
    && history.reduce((total, message) => total + message.content.length, 0) > 7000
  ) {
    history.splice(0, 2);
  }
  return history;
}

function formatTime(date: string) {
  return new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(new Date(date));
}

export function LiveChatWidget() {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [retryState, setRetryState] = useState<RetryState | null>(null);
  const [hasLoadedSession, setHasLoadedSession] = useState(false);
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const launcherRef = useRef<HTMLButtonElement>(null);
  const transcriptRef = useRef<HTMLDivElement>(null);
  const requestRef = useRef<AbortController | null>(null);
  const requestSequenceRef = useRef(0);

  useEffect(() => {
    const saved = readSavedMessages();
    setMessages(saved);
    const lastMessage = saved[saved.length - 1];
    if (lastMessage?.role === 'user' && !lastMessage.complete) {
      setRetryState({
        question: lastMessage.content,
        userMessageId: lastMessage.id,
        history: getHistory(saved.slice(0, -1)),
        detail: 'That message did not receive a reply.',
      });
    }
    setHasLoadedSession(true);
  }, []);

  useEffect(() => {
    if (isOpen) composerRef.current?.focus();
  }, [isOpen]);

  useEffect(() => {
    if (isOpen && transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
    }
  }, [isOpen, messages, isLoading, retryState]);

  useEffect(() => () => requestRef.current?.abort(), []);

  if (
    pathname?.startsWith('/support-call')
    || pathname?.startsWith('/admin/support-calls')
  ) {
    return null;
  }

  function closeChat() {
    setIsOpen(false);
    window.requestAnimationFrame(() => launcherRef.current?.focus());
  }

  function startNewChat() {
    requestSequenceRef.current += 1;
    requestRef.current?.abort();
    requestRef.current = null;
    setIsLoading(false);
    setRetryState(null);
    setMessages([]);
    saveMessages([]);
    composerRef.current?.focus();
  }

  async function sendMessage(
    question: string,
    history: Array<{ role: MessageRole; content: string }>,
    existingMessageId?: string,
  ) {
    if (isLoading || !question.trim()) return;

    const userMessage = existingMessageId
      ? messages.find((message) => message.id === existingMessageId)
      : createMessage('user', question.trim(), false);
    if (!userMessage) return;

    const visibleMessages = existingMessageId ? messages : [...messages, userMessage];
    if (!existingMessageId) {
      setMessages(visibleMessages);
      saveMessages(visibleMessages);
    }

    const requestId = requestSequenceRef.current + 1;
    requestSequenceRef.current = requestId;
    const controller = new AbortController();
    requestRef.current = controller;
    setRetryState(null);
    setIsLoading(true);

    try {
      const { data } = await supportChatClient.post<{ content: string }>(
        '/ai/support-chat/',
        { message: question.trim(), history },
        { signal: controller.signal },
      );
      if (requestSequenceRef.current !== requestId) return;
      const updatedMessages = [
        ...visibleMessages.map((message) => (
          message.id === userMessage.id ? { ...message, complete: true } : message
        )),
        createMessage('assistant', data.content, true),
      ];
      setMessages(updatedMessages);
      saveMessages(updatedMessages);
    } catch (error) {
      if (requestSequenceRef.current !== requestId || axios.isCancel(error)) return;
      setRetryState({
        question: question.trim(),
        userMessageId: userMessage.id,
        history,
        detail: readableError(error),
      });
    } finally {
      if (requestSequenceRef.current === requestId) {
        requestRef.current = null;
        setIsLoading(false);
      }
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const question = draft.trim();
    if (!question || isLoading) return;
    setDraft('');
    void sendMessage(question, getHistory(messages));
  }

  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  return (
    <div className={styles.widget}>
      {isOpen && (
        <section
          className={styles.panel}
          id="ess-support-chat-panel"
          aria-label="ESS AI support chat"
          role="dialog"
          aria-modal="false"
          aria-labelledby="ess-chat-title"
        >
          <header className={styles.header}>
            <div className={styles.brandIcon} aria-hidden="true">
              <MessageCircle size={20} strokeWidth={2.2} />
            </div>
            <div className={styles.heading}>
              <h2 id="ess-chat-title">Ask ESS</h2>
              <span><i aria-hidden="true" /> AI support · not a live agent</span>
            </div>
            <div className={styles.headerActions}>
              <button
                type="button"
                className={styles.iconButton}
                onClick={startNewChat}
                disabled={!hasLoadedSession || isLoading}
                aria-label="Start a new chat"
                title="New chat"
              >
                <RefreshCw size={17} />
              </button>
              <button
                type="button"
                className={styles.iconButton}
                onClick={closeChat}
                aria-label="Minimize support chat"
                title="Minimize"
              >
                <Minimize2 size={17} />
              </button>
              <button
                type="button"
                className={`${styles.iconButton} ${styles.closeButton}`}
                onClick={closeChat}
                aria-label="Close support chat"
                title="Close"
              >
                <X size={18} />
              </button>
            </div>
          </header>

          <div className={styles.transcript} ref={transcriptRef} role="log" aria-live="polite" aria-relevant="additions text">
            {!messages.length && (
              <div className={styles.welcome}>
                <span className={styles.welcomeEyebrow}>ETHIOPIAN STARTUP SCHOOL</span>
                <h3>How can we help you today?</h3>
                <p>Ask about learning at ESS, courses, or finding support. I’m an AI assistant, not a person.</p>
                <div className={styles.starters} aria-label="Suggested questions">
                  {STARTER_PROMPTS.map((prompt) => (
                    <button
                      type="button"
                      key={prompt}
                      className={styles.starter}
                      disabled={isLoading || !hasLoadedSession}
                      onClick={() => void sendMessage(prompt, [])}
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((message) => (
              <article
                key={message.id}
                className={`${styles.message} ${message.role === 'user' ? styles.userMessage : styles.assistantMessage}`}
              >
                {message.role === 'assistant' && (
                  <span className={styles.assistantMark} aria-hidden="true">E</span>
                )}
                <div className={styles.messageContent}>
                  <p>{message.content}</p>
                  <time dateTime={message.createdAt}>
                    {formatTime(message.createdAt)}
                    {!message.complete && <span className={styles.deliveryState}>{isLoading ? ' · Sending' : ' · Not sent'}</span>}
                  </time>
                </div>
              </article>
            ))}

            {isLoading && (
              <div className={styles.typing} role="status" aria-label="ESS assistant is replying">
                <span /><span /><span />
                <span className={styles.typingLabel}>Preparing a helpful answer…</span>
              </div>
            )}

            {retryState && !isLoading && (
              <div className={styles.error} role="alert">
                <p>{retryState.detail}</p>
                <div className={styles.errorActions}>
                  <button
                    type="button"
                    className={styles.retryButton}
                    onClick={() => void sendMessage(
                      retryState.question,
                      retryState.history,
                      retryState.userMessageId,
                    )}
                  >
                    <RefreshCw size={14} /> Try again
                  </button>
                  <Link href="/support-call" onClick={closeChat}>Contact ESS support</Link>
                </div>
              </div>
            )}
          </div>

          <footer className={styles.footer}>
            <div className={styles.humanLink}>
              <LifeBuoy size={15} aria-hidden="true" />
              <span>Need a person?</span>
              <Link href="/support-call" onClick={closeChat}>Request support</Link>
            </div>
            <form className={styles.composer} onSubmit={handleSubmit}>
              <label className={styles.srOnly} htmlFor="ess-chat-message">Your message</label>
              <textarea
                id="ess-chat-message"
                ref={composerRef}
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={handleComposerKeyDown}
                placeholder="Write a message…"
                maxLength={2000}
                rows={1}
                disabled={isLoading || !hasLoadedSession}
              />
              <button
                type="submit"
                className={styles.sendButton}
                disabled={!draft.trim() || isLoading || !hasLoadedSession}
                aria-label="Send message"
                title="Send message"
              >
                <Send size={17} />
              </button>
            </form>
            <p className={styles.privacyNote}>Don’t share passwords or private account details.</p>
          </footer>
        </section>
      )}

      <button
        ref={launcherRef}
        type="button"
        className={styles.launcher}
        onClick={() => setIsOpen(true)}
        aria-expanded={isOpen}
        aria-controls="ess-support-chat-panel"
        aria-label="Open ESS support chat"
        hidden={isOpen}
      >
        <span className={styles.launcherIcon} aria-hidden="true"><MessageCircle size={21} /></span>
        <span className={styles.launcherText}>
          <strong>Ask ESS</strong>
          <small>AI support</small>
        </span>
        <span className={styles.launcherDot} aria-hidden="true" />
      </button>
    </div>
  );
}
