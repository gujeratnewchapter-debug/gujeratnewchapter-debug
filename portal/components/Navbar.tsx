'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Lightbulb, ChevronDown, Search, Menu, X } from 'lucide-react';
import { useAuth } from '@/lib/auth-context';
import { useI18n, LANGUAGES } from '@/lib/i18n';
import { AuthModal } from './AuthModal';

export function Navbar() {
  const { user, isAuthenticated, signOut } = useAuth();
  const { lang, setLang, t } = useI18n();
  const [langOpen, setLangOpen] = useState(false);
  const [authOpen, setAuthOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [search, setSearch] = useState('');
  const pathname = usePathname();
  const router = useRouter();

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    router.push(`/courses?search=${encodeURIComponent(search)}`);
    setMenuOpen(false);
  }

  function closeAllMenus() {
    setLangOpen(false);
    setProfileOpen(false);
    setMenuOpen(false);
  }

  return (
    <>
      <header className="site-header" suppressHydrationWarning>
        <div className="container header-inner">
          <Link href="/" className="brand-link">
            <Lightbulb size={22} color="var(--accent)" fill="var(--accent)" />
            Ethiopian Startup School
          </Link>

          <nav className="desktop-nav">
            <Link href="/" className={pathname === '/' ? 'active' : ''}>{t('home')}</Link>
            <Link href="/courses" className={pathname?.startsWith('/courses') ? 'active' : ''}>{t('courses')}</Link>
            <Link href="/ai-tutor" className={pathname === '/ai-tutor' ? 'active' : ''}>{t('aiTutor')}</Link>
            <Link href="/contact" className={pathname === '/contact' ? 'active' : ''}>{t('contactUs')}</Link>
          </nav>

          <form onSubmit={handleSearchSubmit} className="search-form">
            <Search size={15} className="search-icon" />
            <input
              className="input"
              style={{ paddingLeft: 34 }}
              placeholder={t('searchPlaceholder')}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              suppressHydrationWarning
            />
          </form>

          <div className="header-actions">
            <div className="relative">
              <button className="btn lang-btn" onClick={() => setLangOpen((o) => !o)} type="button" aria-expanded={langOpen} suppressHydrationWarning>
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
              <div className="relative profile-menu-wrapper">
                <button className="profile-button" type="button" onClick={() => setProfileOpen((o) => !o)} suppressHydrationWarning>
                  <div className="avatar">{(user?.first_name?.[0] ?? user?.username?.[0] ?? '?').toUpperCase()}</div>
                </button>
                {profileOpen && (
                  <div className="card profile-menu">
                    <Link href="/dashboard" className="menu-link">{t('dashboard')}</Link>
                    <Link href="/profile" className="menu-link">{t('profile')}</Link>
                    <button type="button" className="menu-link" onClick={() => { signOut(); router.push('/'); closeAllMenus(); }}>
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
            <form onSubmit={handleSearchSubmit} className="search-form mobile-search">
              <Search size={15} className="search-icon" />
              <input
                className="input"
                style={{ paddingLeft: 34 }}
                placeholder={t('searchPlaceholder')}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </form>
            <nav className="mobile-links">
              <Link href="/" onClick={() => setMenuOpen(false)} className={pathname === '/' ? 'active' : ''}>{t('home')}</Link>
              <Link href="/courses" onClick={() => setMenuOpen(false)} className={pathname?.startsWith('/courses') ? 'active' : ''}>{t('courses')}</Link>
              <Link href="/ai-tutor" onClick={() => setMenuOpen(false)} className={pathname === '/ai-tutor' ? 'active' : ''}>{t('aiTutor')}</Link>
              {isAuthenticated ? (
                <>
                  <Link href="/dashboard" onClick={() => setMenuOpen(false)}>{t('dashboard')}</Link>
                  <Link href="/profile" onClick={() => setMenuOpen(false)}>{t('profile')}</Link>
                  <button type="button" className="mobile-signout" onClick={() => { signOut(); router.push('/'); setMenuOpen(false); }}>
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

      {authOpen && <AuthModal onClose={() => setAuthOpen(false)} />}
    </>
  );
}
