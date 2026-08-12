'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { Lightbulb, MapPin, Phone, Mail, Globe, Linkedin, Github, Instagram, Facebook, Youtube, Twitter, MessageCircle, Send, BookOpenText, Sparkles, HandCoins } from 'lucide-react';
import { getSiteSettings, apiClient } from '@/lib/api';
import { useI18n } from '@/lib/i18n';

interface SocialLink {
  platform: string;
  url: string;
  label?: string;
}

interface Settings {
  school_name: string; address: string; phone: string; support_email: string;
  bank_name: string; bank_account_name: string; bank_account_number: string; telebirr_number: string;
  social_links?: SocialLink[];
}

const NAV_ITEMS = [
  { href: '/courses', label: 'Courses' },
  { href: '/ai-tutor', label: 'AI Tutor' },
  { href: '/contact', label: 'Contact' },
  { href: '/profile', label: 'Profile' },
];

const SOCIAL_ICON_MAP: Record<string, any> = {
  linkedin: Linkedin,
  github: Github,
  website: Globe,
  instagram: Instagram,
  facebook: Facebook,
  youtube: Youtube,
  twitter: Twitter,
  whatsapp: MessageCircle,
  telegram: Send,
  blog: BookOpenText,
  community: Sparkles,
  donation: HandCoins,
};

const FALLBACK: Settings = {
  school_name: 'Ethiopian Startup School', address: 'Addis Ababa, Ethiopia', phone: '+251 94 188 3746',
  support_email: 'tilahunalenee@gmail.com', bank_name: 'Commercial Bank of Ethiopia (CBE)',
  bank_account_name: 'Commercial Bank of Ethiopia', bank_account_number: '', telebirr_number: '+251941883746',
};

export function Footer() {
  const { t } = useI18n();
  const [settings, setSettings] = useState<Settings>(FALLBACK);
  const [socialLinks, setSocialLinks] = useState<SocialLink[]>([]);
  const [form, setForm] = useState({ name: '', email: '', subject: '', message: '' });
  const [sent, setSent] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    getSiteSettings().then((res) => {
      const nextSettings = res.data as Settings;
      setSettings(nextSettings);
      setSocialLinks(nextSettings.social_links ?? []);
    }).catch(() => {});
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setSending(true);
    try {
      await apiClient.post('/contact/', form);
      setSent(true);
    } catch {
      setError('Could not send your message right now — please try again.');
    } finally {
      setSending(false);
    }
  }

  return (
    <footer className="footer-section">
      <div className="container footer-grid">
        <div className="footer-brand">
          <div className="footer-brand-head">
            <Lightbulb size={20} color="var(--accent)" fill="var(--accent)" />
            <span>{settings.school_name}</span>
          </div>
          <p className="footer-note">Practical entrepreneurship, AI, and business training built for learners and innovators.</p>
          <div className="footer-links">
            {NAV_ITEMS.map((item) => (
              <Link key={item.href} href={item.href} className="footer-link">
                {item.label}
              </Link>
            ))}
          </div>
          <div className="footer-socials" style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            {socialLinks.length > 0 ? socialLinks.map((item) => {
              const Icon = SOCIAL_ICON_MAP[item.platform?.toLowerCase()] ?? Globe;
              return (
                <Link key={`${item.platform}-${item.url}`} href={item.url} target="_blank" rel="noreferrer" className="footer-social" aria-label={item.label || item.platform}>
                  <Icon size={16} />
                </Link>
              );
            }) : (
              <p className="footer-meta" style={{ margin: 0 }}>Add social links in admin settings.</p>
            )}
          </div>
        </div>

        <div className="footer-info">
          <div className="footer-meta-row">
            <div className="footer-item"><MapPin size={14} />{settings.address}</div>
            <div className="footer-item"><Phone size={14} />{settings.phone}</div>
            <div className="footer-item"><Mail size={14} />{settings.support_email}</div>
          </div>

          <div className="footer-meta-row">
            <p className="footer-meta-title">{t('supportUs')}</p>
            <p className="footer-meta">{settings.bank_name}</p>
            <p className="footer-meta">Account Name: {settings.bank_account_name}</p>
            <p className="footer-meta">Account Number: {settings.bank_account_number || '—'}</p>
            <p className="footer-meta">Telebirr: {settings.telebirr_number}</p>
          </div>
        </div>

        <div className="footer-form">
          <p className="footer-form-title">{t('contactUs')}</p>
          {sent ? (
            <p className="footer-success">Thanks — your message has been sent.</p>
          ) : (
            <form onSubmit={handleSubmit} className="footer-form-grid">
              {error && <p className="footer-error">{error}</p>}
              <input required className="input" placeholder={t('yourName')} value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} />
              <input required type="email" className="input" placeholder={t('yourEmail')} value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} />
              <input required className="input" placeholder={t('subject')} value={form.subject} onChange={(e) => setForm((f) => ({ ...f, subject: e.target.value }))} />
              <textarea required className="input" rows={5} placeholder={t('message')} value={form.message} onChange={(e) => setForm((f) => ({ ...f, message: e.target.value }))} />
              <button className="btn btn-primary" type="submit" disabled={sending}>{t('sendMessage')}</button>
            </form>
          )}
        </div>
      </div>

      <div className="container footer-bottom">
        <span>© {new Date().getFullYear()} {settings.school_name}. All rights reserved.</span>
        <span>Designed for modern learning with subtle technology motion.</span>
      </div>
    </footer>
  );
}
