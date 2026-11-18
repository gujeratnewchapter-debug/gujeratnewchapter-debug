'use client';

import React, { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Lightbulb, ChevronDown, Menu, X } from 'lucide-react';
import { isSuperAdminUser, useAuth } from '@/lib/auth-context';
import { getAdminSupportCalls, getSupportCallError, SupportCallState } from '@/lib/support-calls';
import { useFeatureFlag } from '@/lib/featureFlags';
import { useI18n, LANGUAGES } from '@/lib/i18n';
import { normalizePublicEnvironmentValue } from '@/lib/http-headers';
import { AuthModal } from './AuthModal';

export function Navbar() {
  const { user, isAuthenticated, signOut } = useAuth();
  const isSuperAdmin = isSuperAdminUser(user);
  const startupToolsEnabled = useFeatureFlag('startup_tools', isAuthenticated);
  const { lang, setLang, t } = useI18n();
  const [langOpen, setLangOpen] = useState(false);
  const [authOpen, setAuthOpen] = useState(false);
  const [authTab, setAuthTab] = useState<'signin' | 'signup'>('signin');
  const [authReturnTo, setAuthReturnTo] = useState<string | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [pendingSupportCount, setPendingSupportCount] = useState(0);
  const [incomingSupportCall, setIncomingSupportCall] = useState<SupportCallState | null>(null);
  const [supportCallAlertError, setSupportCallAlertError] = useState('');
  const pathname = usePathname();
  const router = useRouter();
  const notifiedSupportCallIds = useRef(new Set<string>());

  useEffect(() => {
    if (!isSuperAdmin) return;
    let active = true;

    const checkForIncomingCalls = async () => {
      try {
        const { data } = await getAdminSupportCalls();
        if (!active) return;
        setSupportCallAlertError('');
        const pending = data.filter((call) => call.status === 'pending');
        setPendingSupportCount(pending.length);
        const pendingIds = new Set(pending.map((call) => call.call_id));
        setIncomingSupportCall((current) => (
          current && pendingIds.has(current.call_id) ? current : null
        ));
        for (const call of pending) {
          if (notifiedSupportCallIds.current.has(call.call_id)) continue;
          notifiedSupportCallIds.current.add(call.call_id);
          if (!pathname?.startsWith('/admin/support-calls')) {
            setIncomingSupportCall((current) => current ?? call);
          }
          if (!('Notification' in window) || Notification.permission !== 'granted') continue;

          const notification = new Notification('Incoming ESS support call', {
            body: `${call.display_name} is requesting a ${call.mode} call.`,
            tag: `ess-support-call-${call.call_id}`,
            requireInteraction: true,
          });
          notification.onclick = () => {
            window.focus();
            router.push('/admin/support-calls');
            notification.close();
          };
        }
        for (const callId of notifiedSupportCallIds.current) {
          if (!pendingIds.has(callId)) notifiedSupportCallIds.current.delete(callId);
        }
      } catch (requestError) {
        console.error('Could not check incoming support calls:', requestError);
        setSupportCallAlertError(getSupportCallError(
          requestError,
          'Incoming call alerts are offline. Open Support calls to check the queue.',
        ));
        setPendingSupportCount(0);
      }
    };

    void checkForIncomingCalls();
    const timer = window.setInterval(() => { void checkForIncomingCalls(); }, 6000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [isSuperAdmin, pathname, router]);

  function avatarSource(avatar?: string | null) {
    if (!avatar) return null;
    if (avatar.startsWith('http://') || avatar.startsWith('https://')) return avatar;
    const base = normalizePublicEnvironmentValue(
      process.env.NEXT_PUBLIC_API_BASE_URL,
      'NEXT_PUBLIC_API_BASE_URL',
    ) || (
      process.env.NODE_ENV === 'development'
        ? 'http://localhost:8000/api'
        : 'https://ethiopian-startup-school-api.onrender.com/api'
    );
    return `${base.replace(/\/api\/?$/, '')}${avatar.startsWith('/') ? '' : '/'}${avatar}`;
  }

  const profileAvatar = avatarSource(user?.avatar);
  const profileInitial = (user?.first_name?.[0] ?? user?.username?.[0] ?? '?').toUpperCase();

  useEffect(() => {
    setLangOpen(false);
    setProfileOpen(false);
    setMenuOpen(false);
  }, [pathname]);

  useEffect(() => {
    const handler = (event: Event) => {
      const customEvent = event as CustomEvent<{ tab?: 'signin' | 'signup'; returnTo?: string | null }>;
      setAuthTab(customEvent.detail?.tab ?? 'signin');
      setAuthReturnTo(customEvent.detail?.returnTo ?? null);
      setAuthOpen(true);
    };

    window.addEventListener('open-auth-modal', handler);
    return () => window.removeEventListener('open-auth-modal', handler);
  }, []);

  function closeAllMenus() {
    setLangOpen(false);
    setProfileOpen(false);
    setMenuOpen(false);
  }

  return (
    <>
      <header className="site-header" suppressHydrationWarning data-testid="site-header">
        <div className="container header-inner" suppressHydrationWarning>
          <Link href="/" className="brand-link">
            <Lightbulb className="brand-mark" size={22} color="var(--accent)" fill="var(--accent)" />
            <span className="brand-name">Ethiopian Startup School</span>
          </Link>

          <nav className="desktop-nav" aria-label="Main navigation">
            <Link href="/" className={pathname === '/' ? 'active' : ''}>{t('home')}</Link>
            <Link href="/about-us" className={pathname === '/about-us' ? 'active' : ''}>{t('aboutUs')}</Link>
            <Link href="/courses" className={pathname?.startsWith('/courses') ? 'active' : ''}>{t('courses')}</Link>
            {isAuthenticated && <Link href="/meetings" className={pathname?.startsWith('/meetings') ? 'active' : ''}>Meetings</Link>}
            {isSuperAdmin && <Link href="/admin/support-calls" className={pathname?.startsWith('/admin/support-calls') ? 'active' : ''}>Support calls{pendingSupportCount ? ` (${pendingSupportCount})` : ''}</Link>}
            <Link href="/ai/business-advisor" className={pathname?.startsWith('/ai') ? 'active' : ''}>{t('ai')}</Link>
            <Link href="/services/business-consultant" className={pathname?.startsWith('/services') ? 'active' : ''}>{t('services')}</Link>
            <Link href="/startup-ecosystem" className={pathname?.startsWith('/startup-ecosystem') ? 'active' : ''}>{t('startupEcosystem')}</Link>
          </nav>

          <div className="header-actions">
            <div className="relative">
              <button className="btn lang-btn" onClick={() => { setProfileOpen(false); setLangOpen((o) => !o); }} type="button" aria-expanded={langOpen} suppressHydrationWarning>
                {LANGUAGES.find((l) => l.code === lang)?.label} <ChevronDown size={14} />
              </button>
              {langOpen && (
                <div className="card lang-menu">
                  {LANGUAGES.map((l) => (
                    <button
                      key={l.code}
                      onClick={() => { setLang(l.code); setLangOpen(false); }}
                      type="button"
                      className={l.code === lang ? 'active-item' : ''}
                    >
                      {l.label}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {isAuthenticated ? (
              <div className="relative profile-menu-wrapper" suppressHydrationWarning>
                <button className="profile-button" type="button" onClick={() => { setLangOpen(false); setProfileOpen((o) => !o); }} suppressHydrationWarning>
                  <div className="avatar" suppressHydrationWarning>
                    {profileAvatar ? (
                      <img src={profileAvatar} alt="Profile" style={{ width: '100%', height: '100%', borderRadius: '50%', objectFit: 'cover' }} onError={(event) => { event.currentTarget.style.display = 'none'; }} />
                    ) : profileInitial}
                  </div>
                </button>
                {profileOpen && (
                  <div className="card profile-menu" suppressHydrationWarning>
                    <Link 
                      href="/dashboard" 
                      className="menu-link" 
                      onClick={() => { setProfileOpen(false); }}
                    >
                      {t('dashboard')}
                    </Link>
                    <Link 
                      href="/profile" 
                      className="menu-link" 
                      onClick={() => { setProfileOpen(false); }}
                    >
                      {t('profile')}
                    </Link>
                    {startupToolsEnabled && (
                      <Link
                        href="/startup-workspace"
                        className="menu-link"
                        onClick={() => { setProfileOpen(false); }}
                      >
                        {t('startupWorkspace')}
                      </Link>
                    )}
                    <button 
                      type="button" 
                      className="menu-link" 
                      onClick={async () => { 
                        await signOut();
                        setProfileOpen(false);
                        closeAllMenus(); 
                        router.push('/');
                        router.refresh();
                      }}
                    >
                      {t('logOut')}
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <button className="btn btn-primary" type="button" onClick={() => setAuthOpen(true)}>{t('signIn')}</button>
            )}

            <button className="mobile-menu-button" type="button" onClick={() => setMenuOpen((o) => !o)} aria-label={t('toggleNavigation')}>
              {menuOpen ? <X size={18} /> : <Menu size={18} />}
            </button>
          </div>
        </div>

        {menuOpen && (
          <div className="mobile-nav-overlay" onClick={closeAllMenus} />
        )}

        {menuOpen && (
          <div className="mobile-nav">
            <nav className="mobile-links">
              <Link href="/" onClick={() => setMenuOpen(false)} className={pathname === '/' ? 'active' : ''}>{t('home')}</Link>
              <Link href="/about-us" onClick={() => setMenuOpen(false)}>{t('aboutUs')}</Link>
              <Link href="/courses" onClick={() => setMenuOpen(false)} className={pathname?.startsWith('/courses') ? 'active' : ''}>{t('courses')}</Link>
              <Link href="/ai/business-advisor" onClick={() => setMenuOpen(false)}>{t('ai')}</Link>
              <Link href="/services/business-consultant" onClick={() => setMenuOpen(false)}>{t('services')}</Link>
              <Link href="/startup-ecosystem" onClick={() => setMenuOpen(false)}>{t('startupEcosystem')}</Link>
              {isAuthenticated ? (
                <>
                  <Link href="/dashboard" onClick={() => setMenuOpen(false)}>{t('dashboard')}</Link>
                  <Link href="/meetings" onClick={() => setMenuOpen(false)} className={pathname?.startsWith('/meetings') ? 'active' : ''}>Meetings</Link>
                  {isSuperAdmin && <Link href="/admin/support-calls" onClick={() => setMenuOpen(false)} className={pathname?.startsWith('/admin/support-calls') ? 'active' : ''}>Support calls{pendingSupportCount ? ` (${pendingSupportCount})` : ''}</Link>}
                  {startupToolsEnabled && <Link href="/startup-workspace" onClick={() => setMenuOpen(false)}>{t('startupWorkspace')}</Link>}
                  <Link href="/profile" onClick={() => setMenuOpen(false)} style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                    <span className="avatar" style={{ width: 28, height: 28, fontSize: 12 }}>
                      {profileAvatar ? <img src={profileAvatar} alt="Profile" style={{ width: '100%', height: '100%', borderRadius: '50%', objectFit: 'cover' }} /> : profileInitial}
                    </span>
                    {t('profile')}
                  </Link>
                  <button type="button" className="mobile-signout" onClick={async () => { await signOut(); router.push('/'); router.refresh(); setMenuOpen(false); }}>
                    {t('logOut')}
                  </button>
                </>
              ) : (
                <button type="button" className="btn btn-primary mobile-signin" onClick={() => { setAuthOpen(true); setMenuOpen(false); }}>
                  {t('signIn')}
                </button>
              )}
            </nav>
          </div>
        )}
      </header>

      {incomingSupportCall && !pathname?.startsWith('/admin/support-calls') && (
        <aside
          role="alert"
          style={{
            position: 'fixed',
            zIndex: 1100,
            top: 82,
            right: 18,
            width: 'min(380px, calc(100vw - 36px))',
            padding: 18,
            border: '1px solid #b6e2ce',
            borderRadius: 12,
            background: '#fff',
            boxShadow: '0 18px 48px rgba(18, 59, 93, .2)',
          }}
        >
          <strong style={{ display: 'block', color: '#123b5d', fontSize: 14 }}>
            Incoming {incomingSupportCall.mode} support call
          </strong>
          <span style={{ display: 'block', marginTop: 5, color: '#64757d', fontSize: 12 }}>
            {incomingSupportCall.display_name} is waiting for an administrator.
          </span>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 14 }}>
            <button type="button" className="btn" onClick={() => setIncomingSupportCall(null)}>Dismiss</button>
            <button type="button" className="btn btn-primary" onClick={() => {
              setIncomingSupportCall(null);
              router.push('/admin/support-calls');
            }}>Open support queue</button>
          </div>
        </aside>
      )}
      {supportCallAlertError && isSuperAdmin && !pathname?.startsWith('/admin/support-calls') && (
        <aside
          role="status"
          style={{
            position: 'fixed',
            zIndex: 1100,
            top: 82,
            right: 18,
            width: 'min(380px, calc(100vw - 36px))',
            padding: 14,
            border: '1px solid #efc7c3',
            borderRadius: 12,
            background: '#fff7f6',
            color: '#a03b34',
            fontSize: 12,
            boxShadow: '0 18px 48px rgba(18, 59, 93, .12)',
          }}
        >
          <span>{supportCallAlertError}</span>
          <button type="button" className="btn" onClick={() => router.push('/admin/support-calls')} style={{ marginLeft: 8 }}>
            Check queue
          </button>
        </aside>
      )}

      {authOpen && (
        <AuthModal
          onClose={() => {
            setAuthOpen(false);
            setAuthTab('signin');
            setAuthReturnTo(null);
          }}
          initialTab={authTab}
          initialReturnTo={authReturnTo}
        />
      )}
    </>
  );
}
