'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Lightbulb, ChevronDown, Menu, X } from 'lucide-react';
import { useAuth } from '@/lib/auth-context';
import { useI18n, LANGUAGES } from '@/lib/i18n';
import { AuthModal } from './AuthModal';

export function Navbar() {
  const { user, isAuthenticated, signOut } = useAuth();
  const { lang, setLang, t } = useI18n();
  const [langOpen, setLangOpen] = useState(false);
  const [authOpen, setAuthOpen] = useState(false);
  const [authTab, setAuthTab] = useState<'signin' | 'signup'>('signin');
  const [authReturnTo, setAuthReturnTo] = useState<string | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [search, setSearch] = useState('');
  const pathname = usePathname();
  const router = useRouter();

  function avatarSource(avatar?: string | null) {
    if (!avatar) return null;
    if (avatar.startsWith('http://') || avatar.startsWith('https://')) return avatar;
    const base = process.env.NEXT_PUBLIC_API_BASE_URL || (
      process.env.NODE_ENV === 'development' ? 'http://localhost:8000/api' : ''
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

            <button className="mobile-menu-button" type="button" onClick={() => setMenuOpen((o) => !o)} aria-label="Toggle navigation">
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
