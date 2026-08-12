'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Plus } from 'lucide-react';
import { useAuth } from '@/lib/auth-context';
import { getMyEnrollments, getCourses } from '@/lib/api';
import { useI18n } from '@/lib/i18n';

export default function DashboardPage() {
  const { user, isAuthenticated, isLoading } = useAuth();
  const { t } = useI18n();
  const router = useRouter();
  const [enrollments, setEnrollments] = useState<any[]>([]);
  const [myCourses, setMyCourses] = useState<any[]>([]);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) router.push('/');
  }, [isLoading, isAuthenticated]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!isAuthenticated) return;
    getMyEnrollments().then((res) => setEnrollments(res.data.results ?? res.data)).catch(() => {});
    if (user?.role === 'instructor') {
      getCourses({ instructor: user.id }).then((res) => {
        setMyCourses(res.data.results ?? res.data);
      }).catch(() => {});
    } else if (user?.role === 'super_admin') {
      getCourses().then((res) => {
        setMyCourses(res.data.results ?? res.data);
      }).catch(() => {});
    }
  }, [isAuthenticated, user]);

  if (isLoading || !isAuthenticated) return <div className="container section">Loading...</div>;

  return (
    <div className="container section">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 18, marginBottom: 32 }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 18, alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h1 style={{ fontSize: 28, marginBottom: 6 }}>Welcome back, {user?.first_name || user?.username}</h1>
            <p style={{ color: 'var(--text-muted)', margin: 0 }}>{t('yourProgress')}</p>
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <button className="btn btn-primary" onClick={() => router.push('/courses')}>Browse courses</button>
            <button className="btn" onClick={() => router.push('/ai-tutor')}>Open AI Tutor</button>
            <button className="btn" onClick={() => router.push('/profile')}>{t('profile')}</button>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 14 }}>
          <div className="card">
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>Enrolled courses</p>
            <p style={{ fontSize: 32, fontWeight: 700, margin: 0 }}>{enrollments.length}</p>
          </div>
          <div className="card">
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>Active modules</p>
            <p style={{ fontSize: 32, fontWeight: 700, margin: 0 }}>{enrollments.reduce((sum, e) => sum + (e.lessons_completed || 0), 0)}</p>
          </div>
          <div className="card">
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>Your role</p>
            <p style={{ fontSize: 32, fontWeight: 700, margin: 0 }}>{user?.role ?? 'Student'}</p>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 18, marginBottom: 40 }}>
        {enrollments.map((e: any) => (
          <Link key={e.id} href={`/courses/${e.course_detail?.slug}`} className="card" style={{ display: 'block' }}>
            <p style={{ fontWeight: 600, marginBottom: 6 }}>{e.course_detail?.title}</p>
            <div style={{ height: 6, background: 'var(--surface-2)', borderRadius: 99, overflow: 'hidden', margin: '8px 0' }}>
              <div style={{ width: `${e.progress_percent}%`, height: '100%', background: 'var(--brand)' }} />
            </div>
            <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>{e.progress_percent}% complete</p>
          </Link>
        ))}
        {enrollments.length === 0 && (
          <div className="card">
            <p style={{ color: 'var(--text-muted)' }}>You haven't enrolled in a course yet.</p>
            <Link href="/courses" className="btn btn-primary" style={{ marginTop: 12, display: 'inline-flex' }}>Browse Courses</Link>
          </div>
        )}
      </div>

      {(user?.role === 'instructor' || user?.role === 'super_admin') && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h2 style={{ fontSize: 20 }}>{user?.role === 'super_admin' ? 'All Courses' : 'Your Courses'}</h2>
            <button className="btn btn-primary" onClick={() => router.push('/instructor/courses/new')}>
              <Plus size={15} /> New Course
            </button>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 16 }}>
            {myCourses.map((c: any) => (
              <Link key={c.id} href={`/instructor/courses/${c.id}/edit`} className="card">
                <p style={{ fontWeight: 600 }}>{c.title}</p>
                <span className="badge" style={{ marginTop: 8, display: 'inline-block' }}>{c.status}</span>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
