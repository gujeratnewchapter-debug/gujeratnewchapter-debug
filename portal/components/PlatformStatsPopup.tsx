'use client';

import { useEffect, useRef, useState } from 'react';
import { BarChart3, X } from 'lucide-react';
import { getPlatformStats } from '@/lib/api';
import { useI18n } from '@/lib/i18n';

type Stat = { metric: string; label: string; translations?: Record<string, string>; value: number };

export function PlatformStatsPopup() {
  const { lang } = useI18n();
  const [stats, setStats] = useState<Stat[]>([]);
  const [open, setOpen] = useState(false);
  const modalRef = useRef<HTMLElement>(null);
  useEffect(() => { getPlatformStats().then(({ data }) => setStats(data)).catch(() => setStats([])); }, []);
  useEffect(() => {
    if (!open) return;
    const previousActive = document.activeElement as HTMLElement | null;
    const handleKeyDown = (event: KeyboardEvent) => { if (event.key === 'Escape') setOpen(false); };
    document.body.style.overflow = 'hidden';
    document.addEventListener('keydown', handleKeyDown);
    modalRef.current?.querySelector<HTMLElement>('button')?.focus();
    return () => { document.body.style.overflow = ''; document.removeEventListener('keydown', handleKeyDown); previousActive?.focus(); };
  }, [open]);
  if (!stats.length) return null;
  return <>
    <button className="platform-stats-trigger" onClick={() => setOpen(true)} aria-label="View platform statistics"><BarChart3 size={17} /><span>Platform stats</span></button>
    {open && <div className="platform-stats-backdrop" onClick={() => setOpen(false)} role="presentation"><section ref={modalRef} className="platform-stats-modal" onClick={(event) => event.stopPropagation()} role="dialog" aria-modal="true" aria-labelledby="platform-stats-title"><header><div><span className="about-label">Ethiopian Startup School</span><h2 id="platform-stats-title">Platform statistics</h2></div><button type="button" className="ai-icon-button" onClick={() => setOpen(false)} aria-label="Close statistics"><X size={19} /></button></header><div className="platform-stats-grid">{stats.map((stat) => <div className="platform-stat" key={stat.metric}><strong>{stat.value.toLocaleString()}</strong><span>{stat.translations?.[lang] || stat.label}</span></div>)}</div><p className="platform-stats-note">Live counts are updated from available platform data. Admin overrides are used only when configured.</p></section></div>}
  </>;
}