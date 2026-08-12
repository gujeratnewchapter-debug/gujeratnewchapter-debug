'use client';

import React, { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Search } from 'lucide-react';
import { getCourses, getCategories } from '@/lib/api';
import { CourseCard } from '@/components/CourseCard';

function CoursesInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [search, setSearch] = useState(searchParams.get('search') ?? '');
  const [category, setCategory] = useState(searchParams.get('category') ?? '');
  const [level, setLevel] = useState(searchParams.get('level') ?? '');
  const [courses, setCourses] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCategories().then((res) => setCategories(res.data.results ?? res.data)).catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    const params: Record<string, any> = {};
    if (search) params.search = search;
    if (category) params.category = category;
    if (level) params.level = level;

    const query = new URLSearchParams(params as any).toString();
    router.replace(query ? `/courses?${query}` : '/courses');

    getCourses(params).then((res) => setCourses(res.data.results ?? res.data)).finally(() => setLoading(false));
  }, [search, category, level]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="container section">
      <h1 style={{ fontSize: 26, marginBottom: 20 }}>Explore Courses</h1>

      <div style={{ display: 'flex', gap: 10, marginBottom: 28, flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: 220 }}>
          <Search size={15} style={{ position: 'absolute', left: 12, top: 11, color: 'var(--text-muted)' }} />
          <input className="input" style={{ paddingLeft: 34 }} placeholder="Search startup, marketing, finance..." value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <select className="input" style={{ maxWidth: 200 }} value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">All categories</option>
          {categories.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <select className="input" style={{ maxWidth: 180 }} value={level} onChange={(e) => setLevel(e.target.value)}>
          <option value="">All levels</option>
          <option value="beginner">Beginner</option>
          <option value="intermediate">Intermediate</option>
          <option value="advanced">Advanced</option>
        </select>
      </div>

      {loading ? (
        <p style={{ color: 'var(--text-muted)' }}>Loading...</p>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 20 }}>
          {courses.map((c: any) => <CourseCard key={c.id} course={c} />)}
          {courses.length === 0 && <p style={{ color: 'var(--text-muted)' }}>No courses match your search.</p>}
        </div>
      )}
    </div>
  );
}

export default function CoursesPage() {
  return (
    <Suspense fallback={<div className="container section">Loading...</div>}>
      <CoursesInner />
    </Suspense>
  );
}
