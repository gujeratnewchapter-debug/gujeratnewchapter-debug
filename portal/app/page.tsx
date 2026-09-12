'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { Search, Sparkles, GraduationCap, Rocket, LineChart, Award, BookOpen, Users } from 'lucide-react';

import { getCourses, getCategories, getSiteSettings, getPageContent } from '@/lib/api';

function getHeroImageSource(heroSettings: any) {
  const uploadedSources = (heroSettings?.hero_images ?? [])
    .map((image: any) => image?.image)
    .filter(Boolean);

  const preferred = [
    ...(heroSettings?.hero_image ? [heroSettings.hero_image] : []),
    ...uploadedSources,
  ];

  return preferred.find((src) => !!src) ?? null;
}
import { useAuth } from '@/lib/auth-context';
import { useI18n } from '@/lib/i18n';
import { CourseCard } from '@/components/CourseCard';
import { TechVisuals } from '@/components/TechVisuals';

const AI_MODES = [
  { icon: GraduationCap, label: 'AI Tutor', mode: 'tutor', desc: 'Explains concepts, summarizes lessons, and drills you with practice quizzes whenever you\u2019re stuck.' },
  { icon: Rocket, label: 'AI Startup Mentor', mode: 'mentor', desc: 'Ask about fundraising, market research, MVPs, and the lean-startup playbook \u2014 grounded in your course material.' },
  { icon: LineChart, label: 'AI Business Coach', mode: 'coach', desc: 'Builds business plans, SWOT analyses, and financial projections with you, step by step.' },
];

const STEPS = [
  { title: 'Enroll in a course', desc: 'Pick a path in entrepreneurship, AI, finance, marketing, or leadership \u2014 most start free.' },
  { title: 'Learn with AI at every step', desc: 'Watch, read, and ask your AI Tutor questions the moment something didn\u2019t click.' },
  { title: 'Pass to unlock, then get certified', desc: 'Clear each lesson\u2019s quiz to move forward, and earn a QR-verified certificate on completion.' },
];
function resolveImageUrl(image?: string | null) {
  if (!image) return null;
  if (image.startsWith('http://') || image.startsWith('https://')) return image;
  const base = process.env.NEXT_PUBLIC_API_BASE_URL || (
    process.env.NODE_ENV === 'development' ? 'http://localhost:8000/api' : ''
  );
  const origin = base.replace(/\/api\/?$/, '');
  return `${origin}${image.startsWith('/') ? '' : '/'}${image}`;
}
export default function HomePage() {
  const { t, lang } = useI18n();
  const { isAuthenticated } = useAuth();
  const router = useRouter();
  const [search, setSearch] = useState('');
  const [courses, setCourses] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [courseCount, setCourseCount] = useState<number | null>(null);
  const [heroSettings, setHeroSettings] = useState<any>(null);
  const [homeContent, setHomeContent] = useState<any>(null);

  const heroImageSource = getHeroImageSource(heroSettings);
  const activeHeroUrl = heroImageSource && (typeof heroImageSource === 'string' && (heroImageSource.startsWith('http://') || heroImageSource.startsWith('https://')) ? heroImageSource : resolveImageUrl(heroImageSource as string));

  useEffect(() => {
    const loadSiteContent = () => {
      getCourses().then((res) => {
        const all = res.data.results ?? res.data;
        setCourses(all.slice(0, 6));
        setCourseCount(res.data.count ?? all.length);
      }).catch((err) => { console.error('Failed to load courses:', err); });
      getCategories().then((res) => setCategories(res.data.results ?? res.data)).catch((err) => { console.error('Failed to load categories:', err); });
      getSiteSettings().then((res) => setHeroSettings(res.data)).catch((err) => { console.error('Failed to load site settings:', err); });
      getPageContent('home').then((res) => setHomeContent(res.data)).catch(() => undefined);
    };

    loadSiteContent();
  }, []);

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    router.push(`/courses?search=${encodeURIComponent(search)}`);
  }

  const localizedHome = homeContent?.content?.[lang] ?? {};
  const homeSections = homeContent?.sections ?? [];
  const homeItems = (key: string) => {
    const section = homeSections.find((item: any) => item.key === key);
    const content = section?.content?.[lang] ?? section?.content ?? {};
    return content.items ?? section?.content?.items ?? [];
  };
  const configuredModes = homeItems('ai-showcase');
  const aiModes = (configuredModes.length ? configuredModes : AI_MODES).map((item: any, index: number) => {
    const values = Array.isArray(item) ? { label: item[0], desc: item[1], mode: item[2] } : item;
    const fallback = AI_MODES[index % AI_MODES.length];
    return { ...fallback, ...values, mode: values.mode || fallback.mode };
  });
  const configuredSteps = homeItems('how-it-works');
  const steps = (configuredSteps.length ? configuredSteps : STEPS).map((item: any, index: number) => Array.isArray(item) ? { title: item[0], desc: item[1] } : item || STEPS[index]);

  return (
    <div>
      <div className="woven-band" />

      <section className="hero-section compact-home-hero" style={{ paddingTop: 12, paddingBottom: 14, minHeight: 0 }}>
        <TechVisuals className="hero-tech-visuals" />
        {activeHeroUrl ? (
          <div className="hero-media" aria-hidden="true">
            <Image src={activeHeroUrl} alt={heroSettings?.hero_title || 'Hero image'} fill priority sizes="100vw" className="hero-image" />
          </div>
        ) : null}

        <div className="container hero-inner" style={{ maxWidth: 980, textAlign: 'center', paddingTop: 0, paddingBottom: 0 }}>
          <div className="badge" style={{ marginBottom: 8 }}>
            <Sparkles size={13} style={{ marginRight: 6 }} /> {heroSettings?.hero_title || t('heroTitle')}
          </div>
          <h1 className="hero-title" style={{ fontSize: 40, lineHeight: 1.06, margin: '0 0 10px', fontWeight: 700 }}>
            {heroSettings?.hero_title || t('heroTitle')}
          </h1>
          <p className="hero-subtitle" style={{ fontSize: 16, marginBottom: 12, maxWidth: 680, marginLeft: 'auto', marginRight: 'auto' }}>
            {heroSettings?.hero_subtitle || t('heroSubtitle')}
          </p>

          <form className="home-search-form" onSubmit={handleSearch} style={{ display: 'flex', gap: 8, maxWidth: 560, margin: '0 auto', alignItems: 'center', flexWrap: 'wrap' }}>
            <div style={{ position: 'relative', flex: 1, minWidth: 220 }}>
              <Search size={16} style={{ position: 'absolute', left: 14, top: 13, color: 'var(--text-muted)' }} />
              <input className="input" style={{ paddingLeft: 38 }} placeholder={t('searchPlaceholder')} value={search} onChange={(e) => setSearch(e.target.value)} />
            </div>
            <button className="btn btn-accent" type="submit" style={{ transform: 'translateZ(0)' }}>{t('exploreCourses')}</button>
          </form>

          {courseCount !== null && courseCount > 0 && (
            <p style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 16 }}>
              {courseCount} course{courseCount !== 1 ? 's' : ''} live on the platform right now
            </p>
          )}
        </div>
        <div className="hero-decor" aria-hidden>
          <div className="floating-blob blob-1" />
          <div className="floating-blob blob-2" />
          <div className="floating-blob blob-3" />
        </div>
      </section>

      {categories.length > 0 && (
        <section className="container home-category-list" style={{ display: 'flex', gap: 10, flexWrap: 'wrap', justifyContent: 'center', marginBottom: 48 }}>
          {categories.map((c: any) => (
            <Link key={c.id} href={`/courses?category=${c.id}`} className="badge" style={{ fontSize: 13, padding: '6px 14px' }}>
              {c.name}
            </Link>
          ))}
        </section>
      )}

      {/* AI showcase */}
      <section className="container section home-ai-section" style={{ paddingTop: 8 }}>
        <div className="home-section-heading" style={{ textAlign: 'center', marginBottom: 32 }}>
          <h2 style={{ fontSize: 26, margin: '0 0 8px' }}>{localizedHome.ai_title || homeSections.find((item: any) => item.key === 'ai-showcase')?.title || 'Three AI companions, one goal'}</h2>
          <p style={{ color: 'var(--text-muted)', maxWidth: 480, margin: '0 auto' }}>
            {localizedHome.ai_description || homeSections.find((item: any) => item.key === 'ai-showcase')?.body || 'Every course comes with an AI assistant that switches roles depending on what you need.'}
          </p>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 20 }}>
          {aiModes.map((m: any) => (
            <div key={m.label} className="feature-card home-ai-card">
              <m.icon size={22} color="var(--brand)" style={{ marginBottom: 12 }} />
              <p style={{ fontWeight: 600, margin: '0 0 6px' }}>{m.label}</p>
              <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0, lineHeight: 1.5 }}>{m.desc}</p>
              <Link href={`/ai-tutor?mode=${m.mode}`} className="btn btn-primary" style={{ display: 'inline-flex', marginTop: 14 }}>
                Open {m.label}
              </Link>
            </div>
          ))}
        </div>
        </section>

      {/* How it works */}
      <section className="container section home-steps-section">
        <h2 className="home-section-title" style={{ fontSize: 26, marginBottom: 28, textAlign: 'center' }}>How it works</h2>
        <div className="home-steps-list" style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 560, margin: '0 auto' }}>
          {steps.map((s: any, i: number) => (
            <div key={s.title} className="step-item">
              <span className="step-num">{String(i + 1).padStart(2, '0')}</span>
              <div>
                <p style={{ fontWeight: 600, margin: '0 0 4px', fontSize: 16 }}>{s.title}</p>
                <p style={{ color: 'var(--text-muted)', margin: 0, fontSize: 14, lineHeight: 1.5 }}>{s.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Feature grid */}
      <section className="container section home-feature-section">
        <div className="home-feature-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 20 }}>
          <div className="feature-card home-feature-card">
            <BookOpen size={20} color="var(--accent)" style={{ marginBottom: 10 }} />
            <p style={{ fontWeight: 600, margin: '0 0 4px' }}>Structured curriculum</p>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>Video, text, PDFs, and slides organized into modules and lessons.</p>
          </div>
          <div className="feature-card home-feature-card">
            <Award size={20} color="var(--accent)" style={{ marginBottom: 10 }} />
            <p style={{ fontWeight: 600, margin: '0 0 4px' }}>Pass to progress</p>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>Score 80% on each lesson quiz to unlock the next — retry as many times as you need.</p>
          </div>
          <div className="feature-card home-feature-card">
            <Users size={20} color="var(--accent)" style={{ marginBottom: 10 }} />
            <p style={{ fontWeight: 600, margin: '0 0 4px' }}>Built for Ethiopia</p>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: 0 }}>Telebirr and CBE Birr support, with Amharic, Afaan Oromo, and Tigrinya on the way.</p>
          </div>
        </div>
      </section>

      <section className="container section home-courses-section">
        <h2 className="home-section-title" style={{ fontSize: 22, marginBottom: 20 }}>{t('exploreCourses')}</h2>
        <div className="home-course-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 20 }}>
          {courses.map((course: any) => (
            <CourseCard key={course.id} course={course} />
          ))}
          {courses.length === 0 && <p style={{ color: 'var(--text-muted)' }}>Courses will appear here once published.</p>}
        </div>
      </section>

    </div>
  );
}
