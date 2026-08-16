'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getCourse, getLesson, getMyEnrollments, markLessonComplete, getSection, getQuizzesForLesson } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';

export default function LessonPage() {
  const { slug, lessonId } = useParams<{ slug: string; lessonId: string }>();
  const router = useRouter();
  const { isBackendAuthenticated } = useAuth();
  const [lesson, setLesson] = useState<any>(null);
  const [course, setCourse] = useState<any>(null);
  const [enrollment, setEnrollment] = useState<any>(null);
  const [quizId, setQuizId] = useState<number | null>(null);
  const [completing, setCompleting] = useState(false);

  const allLessons = useMemo(
    () => course?.sections?.flatMap((section: any) => section.lessons ?? []) ?? [],
    [course],
  );
  const currentLessonIndex = allLessons.findIndex((item: any) => item.id === Number(lessonId));
  const nextLesson = allLessons[currentLessonIndex + 1] ?? null;

  useEffect(() => {
    load();
  }, [lessonId]);

  async function load() {
    const { data } = await getLesson(Number(lessonId));
    setLesson(data);

    const sectionRes = await getSection(data.section);
    const sectionData = sectionRes.data;
    const courseId = sectionData.course;

    try {
      const courseRes = await getCourse(courseId);
      setCourse(courseRes.data);
    } catch (err) {
      console.warn('Failed to load course for lesson sidebar:', err);
    }

    if (isBackendAuthenticated) {
      try {
        const my = await getMyEnrollments();
        const list = my.data.results ?? my.data;
        const match = list.find((e: any) => e.course === courseId);
        if (match) setEnrollment(match);
      } catch (err) {
        console.warn('Failed to load enrollment for lesson page:', err);
      }
    }

    try {
      const res = await getQuizzesForLesson(Number(lessonId));
      const qdata = res.data.results ?? res.data;
      if (qdata.length) setQuizId(qdata[0].id);
    } catch (err) {
      console.error('Failed to load quizzes for lesson', lessonId, err);
    }
  }

  async function handleComplete() {
    if (!enrollment) return;
    setCompleting(true);
    try {
      await markLessonComplete(enrollment.id, Number(lessonId));
      if (nextLesson?.id) {
        router.push(`/courses/${slug}/lessons/${nextLesson.id}`);
      } else {
        router.push(`/courses/${slug}`);
      }
    } finally {
      setCompleting(false);
    }
  }

  if (!lesson) return <div className="container section">Loading...</div>;

  return (
    <div className="container section" style={{ maxWidth: 1100 }}>
      <button className="btn" onClick={() => router.push(`/courses/${slug}`)} style={{ marginBottom: 16 }}>← Back to course</button>

      <div style={{ display: 'grid', gridTemplateColumns: '280px minmax(0, 1fr)', gap: 24, alignItems: 'start' }}>
        <aside className="card" style={{ padding: 16, position: 'sticky', top: 90 }}>
          <p style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: 1.1, color: 'var(--text-muted)', margin: '0 0 12px' }}>Course syllabus</p>
          {course?.sections?.map((section: any) => (
            <div key={section.id} style={{ marginBottom: 16 }}>
              <p style={{ fontWeight: 700, margin: '0 0 8px', fontSize: 14 }}>{section.title}</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {section.lessons?.map((item: any) => {
                  const active = item.id === Number(lessonId);
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => router.push(`/courses/${slug}/lessons/${item.id}`)}
                      style={{
                        textAlign: 'left',
                        border: active ? '1px solid var(--brand)' : '1px solid var(--border)',
                        borderRadius: 10,
                        background: active ? 'rgba(20, 184, 166, 0.08)' : 'transparent',
                        color: active ? 'var(--text)' : 'var(--text-muted)',
                        padding: '8px 10px',
                        cursor: 'pointer',
                        fontWeight: active ? 700 : 500,
                      }}
                    >
                      {item.title}
                    </button>
                  );
                })}
              </div>
            </div>
          )) ?? <p style={{ color: 'var(--text-muted)', margin: 0 }}>No lesson list available for this course.</p>}
        </aside>

        <main style={{ minWidth: 0 }}>
          <h1 style={{ fontSize: 24, marginBottom: 16 }}>{lesson.title}</h1>

          {lesson.lesson_type === 'video' && lesson.video_url && (
            <div style={{ position: 'relative', paddingBottom: '56.25%', height: 0, marginBottom: 20 }}>
              <iframe
                src={lesson.video_url.replace('watch?v=', 'embed/')}
                style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', border: 0, borderRadius: 12 }}
                allowFullScreen
              />
            </div>
          )}

          {(lesson.lesson_type === 'pdf' || lesson.lesson_type === 'powerpoint' || lesson.lesson_type === 'audio') && (lesson.file || lesson.source_url) && (
            <a href={lesson.file || lesson.source_url} target="_blank" rel="noreferrer" className="btn btn-primary" style={{ marginBottom: 20, display: 'inline-flex' }}>
              Open {lesson.lesson_type.toUpperCase()}
            </a>
          )}

          {lesson.content_text && (
            <div className="rich-editor-content" dangerouslySetInnerHTML={{ __html: lesson.content_text }} style={{ marginBottom: 20 }} />
          )}

          {lesson.resources?.length > 0 && (
            <div style={{ marginBottom: 20 }}>
              <p style={{ fontWeight: 600, marginBottom: 8 }}>Resources</p>
              {lesson.resources.map((r: any) => (
                <a key={r.id} href={r.file} target="_blank" rel="noreferrer" className="btn" style={{ display: 'inline-flex', marginRight: 8, marginBottom: 8 }}>
                  ⬇ {r.title}
                </a>
              ))}
            </div>
          )}

          {quizId ? (
            <button className="btn btn-primary" onClick={() => router.push(`/quizzes/${quizId}`)}>
              Take the lesson quiz to continue
            </button>
          ) : (
            <button className="btn btn-primary" onClick={handleComplete} disabled={completing}>
              {completing ? 'Saving...' : 'Mark Lesson Complete'}
            </button>
          )}
        </main>
      </div>
    </div>
  );
}
