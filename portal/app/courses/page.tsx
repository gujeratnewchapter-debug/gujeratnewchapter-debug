'use client';

import React, { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Search } from 'lucide-react';
import { getCourses, getCategories } from '@/lib/api';
import { CourseCard } from '@/components/CourseCard';
import { InnovationLoader } from '@/components/InnovationLoader';
import { useI18n } from '@/lib/i18n';

function CoursesInner() {
  const { t } = useI18n();
  const searchParams = useSearchParams();
  const router = useRouter();
  const [search, setSearch] = useState(searchParams.get('search') ?? '');
  const [category, setCategory] = useState(searchParams.get('category') ?? '');
  const [level, setLevel] = useState(searchParams.get('level') ?? '');
  const [courses, setCourses] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCategories().then((res) => setCategories(res.data.results ?? res.data)).catch((err) => { console.error('Failed to load categories:', err); });
  }, []);

  useEffect(() => {
    const params: Record<string, any> = {};
    if (search) params.search = search;
    if (category) params.category = category;
    if (level) params.level = level;

    const query = new URLSearchParams(params as any).toString();
    router.replace(query ? `/courses?${query}` : '/courses');

    let active = true;
    let requestId = 0;
    let lastRefreshAt = Date.now();
    const fetchCourses = (showLoader: boolean) => {
      const currentRequestId = ++requestId;
      if (showLoader) setLoading(true);
      return getCourses(params)
        .then((res) => {
          if (active && currentRequestId === requestId) setCourses(res.data.results ?? res.data);
        })
        .catch((err) => { console.error('Failed to load courses:', err); })
        .finally(() => {
          if (active && currentRequestId === requestId) setLoading(false);
        });
    };
    const searchDelay = window.setTimeout(() => { void fetchCourses(true); }, search ? 220 : 0);
    const refreshVisibleCourses = () => {
      const now = Date.now();
      if (document.visibilityState === 'visible' && now - lastRefreshAt > 1000) {
        lastRefreshAt = now;
        void fetchCourses(false);
      }
    };
    window.addEventListener('focus', refreshVisibleCourses);
    document.addEventListener('visibilitychange', refreshVisibleCourses);

    return () => {
      active = false;
      window.clearTimeout(searchDelay);
      window.removeEventListener('focus', refreshVisibleCourses);
      document.removeEventListener('visibilitychange', refreshVisibleCourses);
    };
  }, [search, category, level, router]);

  return (
    <div className="container section">
      <h1 style={{ fontSize: 26, marginBottom: 20 }}>{t('exploreCoursesTitle')}</h1>

      <div className="course-filters" style={{ display: 'flex', gap: 10, marginBottom: 28, flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: 220 }}>
          <Search size={15} style={{ position: 'absolute', left: 12, top: 11, color: 'var(--text-muted)' }} />
          <input className="input" style={{ paddingLeft: 34 }} placeholder={t('searchCourseTopics')} value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <select className="input" style={{ maxWidth: 200 }} value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">{t('allCategories')}</option>
          {categories.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <select className="input" style={{ maxWidth: 180 }} value={level} onChange={(e) => setLevel(e.target.value)}>
          <option value="">{t('allLevels')}</option>
          <option value="beginner">{t('beginner')}</option>
          <option value="intermediate">{t('intermediate')}</option>
          <option value="advanced">{t('advanced')}</option>
        </select>
      </div>

      {loading ? (
        <InnovationLoader label={t('loadingCourses')} />
      ) : (
        <div className="course-grid" style={{ display: 'grid', gap: 20 }}>
          {courses.map((c: any) => <CourseCard key={c.id} course={c} />)}
          {courses.length === 0 && <p style={{ color: 'var(--text-muted)' }}>{t('noCoursesMatch')}</p>}
        </div>
      )}
    </div>
  );
}

export default function CoursesPage() {
  const { t } = useI18n();
  return (
    <Suspense fallback={<div className="container section"><InnovationLoader label={t('loadingCourses')} /></div>}>
      <CoursesInner />
    </Suspense>
  );
}
