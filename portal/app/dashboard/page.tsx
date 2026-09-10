'use client';

import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { BrainCircuit, CheckCircle2, Plus, Sparkles, Trash2 } from 'lucide-react';
import { useAuth } from '@/lib/auth-context';
import { deleteCourse, getCourses, getInstructorAnalytics, getMyEnrollments } from '@/lib/api';
import { useI18n } from '@/lib/i18n';
import { InnovationLoader } from '@/components/InnovationLoader';

export default function DashboardPage() {
  const { user, isAuthenticated, isBackendAuthenticated, isLoading } = useAuth();
  const { t } = useI18n();
  const router = useRouter();
  const [enrollments, setEnrollments] = useState<any[]>([]);
  const [myCourses, setMyCourses] = useState<any[]>([]);
  const [instructorAnalytics, setInstructorAnalytics] = useState<any>(null);

  useEffect(() => {
    if (!isLoading && !isBackendAuthenticated) router.push('/');
  }, [isLoading, isBackendAuthenticated]);

  useEffect(() => {
    if (!isBackendAuthenticated) return;
    getMyEnrollments().then((res) => setEnrollments(res.data.results ?? res.data)).catch((err) => { console.error('Failed to load enrollments:', err); });
    if (user?.role === 'instructor') {
      getCourses({ instructor: user.id }).then((res) => {
        setMyCourses(res.data.results ?? res.data);
      }).catch((err) => { console.error('Failed to load instructor courses:', err); });
      getInstructorAnalytics().then((res) => setInstructorAnalytics(res.data)).catch((err) => { console.error('Failed to load instructor analytics:', err); });
    } else if (user?.role === 'super_admin') {
      getCourses().then((res) => {
        setMyCourses(res.data.results ?? res.data);
      }).catch((err) => { console.error('Failed to load courses:', err); });
    }
  }, [isBackendAuthenticated, user]);

  async function handleDeleteCourse(course: any) {
    if (!window.confirm(`Delete "${course.title}" and its lessons? This cannot be undone.`)) return;
    try {
      await deleteCourse(course.id);
      setMyCourses((courses) => courses.filter((item) => item.id !== course.id));
      setInstructorAnalytics((current: any) => current ? {
        ...current,
        courses: current.courses.filter((item: any) => item.course_id !== course.id),
        totals: { ...current.totals, courses: Math.max(0, current.totals.courses - 1) },
      } : current);
    } catch (err) {
      console.error('Failed to delete course:', err);
      window.alert('Unable to delete this course. Please try again.');
    }
  }

  const avgProgress = useMemo(
    () => (enrollments.length ? enrollments.reduce((sum, item) => sum + (item.progress_percent ?? 0), 0) / enrollments.length : 0),
    [enrollments],
  );

  const completedCourses = useMemo(
    () => enrollments.filter((item) => (item.progress_percent ?? 0) >= 100).length,
    [enrollments],
  );

  if (isLoading || !isBackendAuthenticated) return <div className="container section"><InnovationLoader label="Loading dashboard" /></div>;

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
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>Avg. progress</p>
            <p style={{ fontSize: 32, fontWeight: 700, margin: 0 }}>{Math.round(avgProgress)}%</p>
          </div>
          <div className="card">
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>Completed</p>
            <p style={{ fontSize: 32, fontWeight: 700, margin: 0 }}>{completedCourses}</p>
          </div>
          <div className="card">
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>Your role</p>
            <p style={{ fontSize: 32, fontWeight: 700, margin: 0 }}>{user?.role ?? 'Student'}</p>
          </div>
        </div>
      </div>

      <div className="card" style={{ padding: 20, marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
          <BrainCircuit size={18} color="var(--brand)" />
          <h2 style={{ fontSize: 18, margin: 0 }}>AI learning companion</h2>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 14 }}>
          <button className="btn btn-primary" onClick={() => router.push('/ai-tutor')}>Ask the AI Tutor</button>
          <button className="btn" onClick={() => router.push('/courses')}>Continue learning</button>
          <button className="btn" onClick={() => router.push('/profile')}>View profile</button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 18, marginBottom: 40 }}>
        {enrollments.map((e: any) => (
          <Link key={e.id} href={`/courses/${e.course_detail?.slug}`} className="card" style={{ display: 'block' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <p style={{ fontWeight: 600, margin: 0 }}>{e.course_detail?.title}</p>
              <CheckCircle2 size={15} color="var(--brand)" />
            </div>
            <div style={{ height: 6, background: 'var(--surface-2)', borderRadius: 99, overflow: 'hidden', margin: '8px 0' }}>
              <div style={{ width: `${e.progress_percent}%`, height: '100%', background: 'var(--brand)' }} />
            </div>
            <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>{e.progress_percent}% complete</p>
          </Link>
        ))}
        {enrollments.length === 0 && (
          <div className="card">
            <p style={{ color: 'var(--text-muted)' }}>You haven&apos;t enrolled in a course yet.</p>
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
          {user?.role === 'instructor' && instructorAnalytics && (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 14, marginBottom: 18 }}>
                {[
                  ['Registered students', instructorAnalytics.totals.registered_students],
                  ['Currently attending', instructorAnalytics.totals.attending_students],
                  ['Completed courses', instructorAnalytics.totals.completed_students],
                  ['Certificates issued', instructorAnalytics.totals.certificates_issued],
                ].map(([label, value]) => (
                  <div className="card" key={String(label)}>
                    <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>{label}</p>
                    <p style={{ fontSize: 30, fontWeight: 700, margin: 0 }}>{value}</p>
                  </div>
                ))}
              </div>
              <div className="card" style={{ marginBottom: 18, overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 720 }}>
                  <thead><tr>{['Course', 'Registered', 'Attending', 'Completed', 'Certificates', 'Avg. progress', 'Status'].map((heading) => <th key={heading} style={{ textAlign: 'left', padding: '10px 8px', borderBottom: '1px solid var(--border)', fontSize: 12 }}>{heading}</th>)}</tr></thead>
                  <tbody>{instructorAnalytics.courses.map((item: any) => <tr key={item.course_id}>
                    <td style={{ padding: '10px 8px', fontWeight: 600 }}>{item.title}</td>
                    <td style={{ padding: '10px 8px' }}>{item.registered_students}</td>
                    <td style={{ padding: '10px 8px' }}>{item.attending_students}</td>
                    <td style={{ padding: '10px 8px' }}>{item.completed_students}</td>
                    <td style={{ padding: '10px 8px' }}>{item.certificates_issued}</td>
                    <td style={{ padding: '10px 8px' }}>{item.average_progress_percent}%</td>
                    <td style={{ padding: '10px 8px' }}>{item.status}</td>
                  </tr>)}</tbody>
                </table>
              </div>
            </>
          )}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 16 }}>
            {myCourses.map((c: any) => (
              <div key={c.id} className="card">
                <Link href={`/instructor/courses/${c.id}/edit`} style={{ display: 'block' }}>
                  <p style={{ fontWeight: 600 }}>{c.title}</p>
                  <span className="badge" style={{ marginTop: 8, display: 'inline-block' }}>{c.status}</span>
                </Link>
                {user?.role === 'instructor' && <button type="button" className="btn" onClick={() => handleDeleteCourse(c)} style={{ marginTop: 14, color: 'var(--danger)', display: 'inline-flex', alignItems: 'center', gap: 6 }}><Trash2 size={14} /> Delete course</button>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
