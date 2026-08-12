'use client';

import React, { useState } from 'react';
import { Mail, MapPin, Phone } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { useI18n } from '@/lib/i18n';

export default function ContactPage() {
  const { t } = useI18n();
  const [form, setForm] = useState({ name: '', email: '', subject: '', message: '' });
  const [status, setStatus] = useState<'idle' | 'sending' | 'success' | 'error'>('idle');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus('sending');
    try {
      await apiClient.post('/contact/', form);
      setStatus('success');
      setForm({ name: '', email: '', subject: '', message: '' });
    } catch {
      setStatus('error');
    }
  }

  return (
    <div className="container section" style={{ maxWidth: 720 }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: 28, alignItems: 'start' }}>
        <div>
          <h1 style={{ fontSize: 28, marginBottom: 12 }}>Contact the team</h1>
          <p style={{ color: 'var(--text-muted)', marginBottom: 24 }}>Send us feedback, ask about instructor approval, or request support for your course.</p>

          <form onSubmit={handleSubmit} style={{ display: 'grid', gap: 14 }}>
            <input className="input" placeholder={t('yourName')} value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} required />
            <input className="input" type="email" placeholder={t('yourEmail')} value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} required />
            <input className="input" placeholder={t('subject')} value={form.subject} onChange={(e) => setForm((f) => ({ ...f, subject: e.target.value }))} required />
            <textarea className="input" rows={5} placeholder={t('message')} value={form.message} onChange={(e) => setForm((f) => ({ ...f, message: e.target.value }))} required />
            <button className="btn btn-primary" type="submit" disabled={status === 'sending'}>
              {status === 'sending' ? 'Sending...' : 'Send message'}
            </button>
            {status === 'success' && <p style={{ color: 'var(--brand)' }}>Message sent successfully.</p>}
            {status === 'error' && <p style={{ color: 'var(--danger)' }}>Unable to send your message. Please try again later.</p>}
          </form>
        </div>

        <div className="card" style={{ padding: 24 }}>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 18 }}>
            <Mail size={18} color="var(--accent)" />
            <div>
              <p style={{ fontWeight: 600, margin: 0 }}>Support email</p>
              <p style={{ color: 'var(--text-muted)', margin: 0 }}>support@ethiopianstartup.school</p>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 18 }}>
            <Phone size={18} color="var(--accent)" />
            <div>
              <p style={{ fontWeight: 600, margin: 0 }}>Phone</p>
              <p style={{ color: 'var(--text-muted)', margin: 0 }}>+251 94 188 3746</p>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <MapPin size={18} color="var(--accent)" />
            <div>
              <p style={{ fontWeight: 600, margin: 0 }}>Location</p>
              <p style={{ color: 'var(--text-muted)', margin: 0 }}>Addis Ababa, Ethiopia</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
