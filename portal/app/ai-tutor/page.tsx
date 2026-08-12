'use client';

import React, { Suspense, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { Send, GraduationCap, Rocket, LineChart, RotateCcw } from 'lucide-react';
import { useAuth } from '@/lib/auth-context';
import { createConversation, sendAIMessage } from '@/lib/api';

const MODES = [
  { key: 'tutor', label: 'AI Tutor', icon: GraduationCap, desc: 'Explain concepts, summarize lessons, generate quizzes',
    prompts: ['Explain this lesson in simpler terms', 'Quiz me on what I just learned', 'Summarize this course so far'] },
  { key: 'mentor', label: 'AI Startup Mentor', icon: Rocket, desc: 'Fundraising, pitch decks, lean startup, market research',
    prompts: ['How do I validate my startup idea?', 'What goes into a seed-stage pitch deck?', 'How do I run customer discovery interviews?'] },
  { key: 'coach', label: 'AI Business Coach', icon: LineChart, desc: 'Business plans, financial projections, SWOT analysis',
    prompts: ['Help me draft a lean business plan', 'Run a SWOT analysis for my idea', 'What should my financial projections include?'] },
];

function AITutorInner() {
  const { isAuthenticated } = useAuth();
  const searchParams = useSearchParams();
  const courseId = searchParams.get('course');
  const [mode, setMode] = useState('tutor');
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const activeMode = MODES.find((m) => m.key === mode)!;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  async function startConversation(selectedMode: string) {
    setMode(selectedMode);
    setMessages([]);
    setConversationId(null);
    if (!isAuthenticated) return;
    const label = MODES.find((m) => m.key === selectedMode)?.label ?? '';
    const { data } = await createConversation(selectedMode, label, courseId ? Number(courseId) : undefined);
    setConversationId(data.id);
    setMessages(data.messages ?? []);
  }

  async function sendText(text: string) {
    if (!text.trim() || !isAuthenticated) return;
    const userMsg = { id: `local-${Date.now()}`, role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setSending(true);
    try {
      let convId = conversationId;
      if (!convId) {
        const { data } = await createConversation(mode, activeMode.label, courseId ? Number(courseId) : undefined);
        convId = data.id;
        setConversationId(convId);
      }
      const { data } = await sendAIMessage(convId!, text);
      setMessages((prev) => [...prev, data]);
    } finally {
      setSending(false);
    }
  }

  function handleSend(e: React.FormEvent) {
    e.preventDefault();
    sendText(input);
  }

  return (
    <div className="container section" style={{ maxWidth: 760 }}>
      <h1 style={{ fontSize: 26, marginBottom: 6 }}>AI Assistant</h1>
      <p style={{ color: 'var(--text-muted)', marginBottom: 24 }}>
        Ask about startups, business models, fundraising, pitch decks, or anything in your courses.
      </p>

      <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' }}>
        {MODES.map((m) => (
          <button
            key={m.key}
            onClick={() => startConversation(m.key)}
            className="btn"
            style={{
              background: mode === m.key ? 'var(--brand)' : 'var(--surface-2)',
              color: mode === m.key ? '#fff' : 'var(--text)',
              flex: '1 1 180px', justifyContent: 'flex-start', gap: 10,
            }}
          >
            <m.icon size={16} /> {m.label}
          </button>
        ))}
      </div>

      {!isAuthenticated ? (
        <div className="card" style={{ textAlign: 'center' }}>
          <p style={{ color: 'var(--text-muted)' }}>Sign in to start chatting with the AI Assistant.</p>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, display: 'flex', flexDirection: 'column', height: 540 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', borderBottom: '1px solid var(--border)' }}>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>{activeMode.desc}</p>
            {messages.length > 0 && (
              <button className="btn" style={{ fontSize: 12, padding: '6px 10px' }} onClick={() => startConversation(mode)}>
                <RotateCcw size={12} /> New chat
              </button>
            )}
          </div>

          <div style={{ flex: 1, overflowY: 'auto', padding: 20, display: 'flex', flexDirection: 'column', gap: 12 }}>
            {messages.length === 0 && (
              <div style={{ textAlign: 'center', marginTop: 24 }}>
                <activeMode.icon size={28} color="var(--brand)" style={{ marginBottom: 12 }} />
                <p style={{ color: 'var(--text-muted)', marginBottom: 20 }}>
                  Ask your first question, or try one of these:
                </p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxWidth: 440, margin: '0 auto' }}>
                  {activeMode.prompts.map((p) => (
                    <button key={p} className="btn" style={{ textAlign: 'left', justifyContent: 'flex-start' }} onClick={() => sendText(p)}>
                      {p}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((m: any) => (
              <div
                key={m.id}
                style={{
                  alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
                  background: m.role === 'user' ? 'var(--brand)' : 'var(--surface-2)',
                  color: m.role === 'user' ? '#fff' : 'var(--text)',
                  padding: '10px 14px', borderRadius: 14, maxWidth: '80%', fontSize: 14, lineHeight: 1.5,
                }}
              >
                {m.content}
                {m.sources?.length > 0 && (
                  <p style={{ fontSize: 11, color: 'var(--accent)', marginTop: 6 }}>Sources: {m.sources.map((s: any) => s.title).join(', ')}</p>
                )}
              </div>
            ))}
            {sending && (
              <div style={{ alignSelf: 'flex-start', background: 'var(--surface-2)', padding: '10px 14px', borderRadius: 14, display: 'flex', gap: 4 }}>
                <span className="typing-dot" /><span className="typing-dot" /><span className="typing-dot" />
              </div>
            )}
            <div ref={bottomRef} />
          </div>
          <form onSubmit={handleSend} style={{ display: 'flex', gap: 8, padding: 14, borderTop: '1px solid var(--border)' }}>
            <input className="input" placeholder="Ask a question..." value={input} onChange={(e) => setInput(e.target.value)} disabled={sending} />
            <button className="btn btn-primary" type="submit" disabled={sending || !input.trim()}><Send size={15} /></button>
          </form>
        </div>
      )}
    </div>
  );
}

export default function AITutorPage() {
  return (
    <Suspense fallback={<div className="container section">Loading...</div>}>
      <AITutorInner />
    </Suspense>
  );
}
