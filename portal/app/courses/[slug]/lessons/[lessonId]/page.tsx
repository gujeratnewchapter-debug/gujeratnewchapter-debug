'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getLesson, getMyEnrollments, markLessonComplete, getSection, getQuizzesForLesson } from '@/lib/api';

export default function LessonPage() {
  const { slug, lessonId } = useParams<{ slug: string; lessonId: string }>();
  const router = useRouter();
  const [lesson, setLesson] = useState<any>(null);
  const [enrollment, setEnrollment] = useState<any>(null);
  const [quizId, setQuizId] = useState<number | null>(null);
  const [completing, setCompleting] = useState(false);

  useEffect(() => {
    load();
  }, [lessonId]);

  async function load() {
    const { data } = await getLesson(Number(lessonId));
    setLesson(data);

    const sectionRes = await getSection(data.section);
    const sectionData = sectionRes.data;
    const courseId = sectionData.course;

    const my = await getMyEnrollments();
    const list = my.data.results ?? my.data;
    const match = list.find((e: any) => e.course === courseId);
    if (match) setEnrollment(match);

    // Find the quiz attached to this lesson, if any
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
      router.push(`/courses/${slug}`);
    } finally {
      setCompleting(false);
    }
  }

  if (!lesson) return <div className="container section">Loading...</div>;

  return (
    <div className="container section" style={{ maxWidth: 760 }}>
      <button className="btn" onClick={() => router.push(`/courses/${slug}`)} style={{ marginBottom: 16 }}>← Back to course</button>
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
    </div>
  );
}
