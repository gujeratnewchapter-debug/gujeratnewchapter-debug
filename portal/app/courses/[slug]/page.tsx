'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import Image from 'next/image';
import { Lock, PlayCircle, FileText, Presentation, Headphones, Code, Radio, BookOpen } from 'lucide-react';
import { getCourses, getMyEnrollments, enroll, getCourse } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';

const ICONS: Record<string, any> = {
  video: PlayCircle, pdf: FileText, powerpoint: Presentation, text: BookOpen,
  interactive_html: Code, coding_exercise: Code, audio: Headphones, live_session: Radio,
};

export default function CourseDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const { isAuthenticated } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [course, setCourse] = useState<any>(null);
  const [enrollment, setEnrollment] = useState<any>(null);
  const [enrolling, setEnrolling] = useState(false);

  useEffect(() => {
    load();
  }, [slug, isAuthenticated]);

  async function load() {
    const idParam = searchParams?.get('id');
    if (idParam) {
      try {
        const { data: detail } = await getCourse(idParam);
        setCourse(detail);
        if (isAuthenticated) {
          const my = await getMyEnrollments();
          const existing = (my.data.results ?? my.data).find((e: any) => e.course === detail.id);
          setEnrollment(existing ?? null);
        }
        return;
      } catch (err) {
        // fall back to search-based lookup below
      }
    }

    const { data } = await getCourses({ search: slug });
    const list = data.results ?? data;
    const match = list.find((c: any) => c.slug === slug) ?? list[0];
    if (!match) {
      setCourse(null);
      return;
    }

    const { data: detail } = await getCourse(match.id);
    setCourse(detail);

    if (isAuthenticated) {
      const my = await getMyEnrollments();
      const existing = (my.data.results ?? my.data).find((e: any) => e.course === detail.id);
      setEnrollment(existing ?? null);
    }
  }

  async function handleEnroll() {
    if (!isAuthenticated) {
      router.push('/');
      return;
    }
    if (!course) return;
    setEnrolling(true);
    try {
      const { data } = await enroll(course.id);
      setEnrollment(data);
    } finally {
      setEnrolling(false);
    }
  }

  if (!course) return <div className="container section">Loading...</div>;

  return (
    <div className="container section">
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 32 }}>
        <div>
          <span className="badge" style={{ marginBottom: 12, display: 'inline-block' }}>{course.category_name}</span>
          <h1 style={{ fontSize: 30, margin: '0 0 8px' }}>{course.title}</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 15, marginBottom: 4 }}>{course.subtitle}</p>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, margin: '12px 0 20px' }}>
            {course.instructor_photo ? (
              <Image src={course.instructor_photo} alt={course.instructor_name} width={32} height={32} style={{ borderRadius: '50%' }} unoptimized />
            ) : (
              <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'var(--surface-2)' }} />
            )}
            <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>By {course.instructor_name}</span>
          </div>

          <div className="rich-editor-content" dangerouslySetInnerHTML={{ __html: course.description }} />

          {course.notes_enabled && course.notes && (
            <div className="card" style={{ marginTop: 20, borderColor: 'var(--brand)' }}>
              <p style={{ fontWeight: 600, marginBottom: 8, fontSize: 13, color: 'var(--brand)' }}>Course Notes</p>
              <div className="rich-editor-content" dangerouslySetInnerHTML={{ __html: course.notes }} />
            </div>
          )}

          <h2 style={{ fontSize: 20, margin: '32px 0 16px' }}>Curriculum</h2>
          {course.sections.map((section: any) => (
            <div key={section.id} className="card" style={{ marginBottom: 14 }}>
              <p style={{ fontWeight: 600, marginBottom: 10 }}>{section.title}</p>
              {section.lessons.map((lesson: any) => {
                const Icon = ICONS[lesson.lesson_type] ?? BookOpen;
                const locked = !lesson.is_unlocked;
                return (
                  <div
                    key={lesson.id}
                    onClick={() => !locked && router.push(`/courses/${slug}/lessons/${lesson.id}`)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 10, padding: '10px 0',
                      borderTop: '1px solid var(--border)', cursor: locked ? 'not-allowed' : 'pointer',
                      opacity: locked ? 0.5 : 1,
                    }}
                  >
                    <Icon size={16} color="var(--text-muted)" />
                    <span style={{ flex: 1, fontSize: 14 }}>{lesson.title}</span>
                    {locked && <Lock size={14} color="var(--text-muted)" />}
                  </div>
                );
              })}
            </div>
          ))}
        </div>

        <div>
          <div className="card">
            <div style={{ height: 160, background: 'var(--surface-2)', borderRadius: 10, marginBottom: 16, position: 'relative', overflow: 'hidden' }}>
              {course.thumbnail && <Image src={course.thumbnail} alt={course.title} fill style={{ objectFit: 'cover' }} unoptimized />}
            </div>
            <p style={{ fontSize: 24, fontWeight: 700, marginBottom: 12 }}>
              {course.is_free ? 'Free' : `${course.price} ETB`}
            </p>
            {enrollment ? (
              <>
                <p style={{ fontSize: 13, color: 'var(--brand)', marginBottom: 10 }}>✓ You're enrolled — {enrollment.progress_percent}% complete</p>
                <button className="btn btn-primary" style={{ width: '100%' }} onClick={() => router.push(`/ai-tutor?course=${course.id}`)}>
                  Ask the AI Tutor about this course
                </button>
              </>
            ) : (
              <button className="btn btn-primary" style={{ width: '100%' }} onClick={handleEnroll} disabled={enrolling}>
                {enrolling ? 'Enrolling...' : course.is_free ? 'Enroll for Free' : 'Enroll Now'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
