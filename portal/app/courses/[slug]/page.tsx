'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { ChevronDown, Lock, PlayCircle, FileText, Presentation, Headphones, Code, Radio, BookOpen } from 'lucide-react';
import { getCourses, getMyEnrollments, enroll, getCourse, getEnrollmentProgress, getQuizzesForCourse } from '@/lib/api';
import { ApiImage } from '@/components/ApiImage';
import { useAuth } from '@/lib/auth-context';
import { InnovationLoader } from '@/components/InnovationLoader';
import { getResumeLessonPath, getSectionContinuePath } from '@/lib/course-navigation';
import { sanitizeRichText } from '@/lib/sanitize-html';

const ICONS: Record<string, any> = {
  video: PlayCircle, pdf: FileText, powerpoint: Presentation, text: BookOpen,
  interactive_html: Code, coding_exercise: Code, audio: Headphones, live_session: Radio,
};

export default function CourseDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const { isAuthenticated, isBackendAuthenticated } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [course, setCourse] = useState<any>(null);
  const [enrollment, setEnrollment] = useState<any>(null);
  const [enrolling, setEnrolling] = useState(false);
  const [openingLesson, setOpeningLesson] = useState(false);
  const [enrollmentError, setEnrollmentError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [courseError, setCourseError] = useState<string | null>(null);
  const [openWeeks, setOpenWeeks] = useState<Record<string, boolean>>({});
  const [finalExam, setFinalExam] = useState<any>(null);
  const [moduleFinalQuizzes, setModuleFinalQuizzes] = useState<Record<string, any>>({});
  const loadRef = useRef<(forceRefresh?: boolean) => Promise<void>>(async () => undefined);
  const autoEnrollCourseId = useRef<number | null>(null);

  const weekGroups = React.useMemo(() => {
    const groups: Record<string, { title: string; sections: any[] }> = {};
    course?.sections?.forEach((section: any) => {
      const sectionTitle = String(section.title);
      const weekNumber = sectionTitle.match(/Week\s+(\d+)/i)?.[1];
      const moduleNumber = sectionTitle.match(/Module\s+(\d+)/i)?.[1];
      const groupNumber = weekNumber ?? moduleNumber ?? String(section.order ?? 1);
      const key = weekNumber ? `week-${groupNumber}` : `module-${groupNumber}`;
      if (!groups[key]) {
        groups[key] = {
          title: !weekNumber
            ? sectionTitle
            : groupNumber === '1'
            ? 'Introduction to Startup Ecosystem'
            : groupNumber === '2'
              ? 'Ideation and Problem Solving'
              : groupNumber === '3'
                ? 'Business Model and Lean Startup'
                : groupNumber === '4'
                  ? 'Market Research and Validation'
                  : groupNumber === '5'
                    ? 'Finance, Legal Structure, and Financial Planning'
                      : groupNumber === '6'
                        ? 'Funding, Pitching, and Investment'
                          : groupNumber === '7'
                            ? 'Building Teams and Go-To-Market (GTM)'
                              : groupNumber === '8'
                                ? 'Scaling, Growth, and Exit'
                  : `Week ${groupNumber}`,
          sections: [],
        };
      }
      groups[key].sections.push(section);
    });
    return Object.entries(groups);
  }, [course]);

  useEffect(() => {
    setLoading(true);
    setCourseError(null);
    setEnrollment(null);
    let lastRefreshAt = Date.now();
    void loadRef.current();
    const refreshCourse = () => {
      const now = Date.now();
      if (document.visibilityState === 'visible' && now - lastRefreshAt > 1000) {
        lastRefreshAt = now;
        void loadRef.current(true);
      }
    };
    window.addEventListener('focus', refreshCourse);
    document.addEventListener('visibilitychange', refreshCourse);
    return () => {
      window.removeEventListener('focus', refreshCourse);
      document.removeEventListener('visibilitychange', refreshCourse);
    };
  }, [slug, isAuthenticated, isBackendAuthenticated]);

  useEffect(() => {
    if (!course?.id || !isBackendAuthenticated) {
      setFinalExam(null);
      setModuleFinalQuizzes({});
      return;
    }
    getQuizzesForCourse(course.id)
      .then((res) => {
        const quizzes = res.data.results ?? res.data;
        setFinalExam(quizzes.find((quiz: any) => quiz.is_final_exam && !quiz.lesson) ?? null);
        setModuleFinalQuizzes(
          quizzes.reduce((acc: Record<string, any>, quiz: any) => {
            if (quiz.is_final_exam && quiz.section && !quiz.lesson) acc[String(quiz.section)] = quiz;
            return acc;
          }, {}),
        );
      })
      .catch(() => {
        setFinalExam(null);
        setModuleFinalQuizzes({});
      });
  }, [course?.id, isBackendAuthenticated]);

  const continueLearning = React.useCallback(async (targetCourse: any, targetEnrollment: any = enrollment) => {
    setEnrollmentError(null);
    setOpeningLesson(true);
    try {
      const { data: accessibleCourse } = await getCourse(targetCourse.id, true);
      setCourse(accessibleCourse);
      if (!targetEnrollment?.id) {
        throw new Error('Your course enrollment could not be loaded. Refresh the page and try again.');
      }
      const { data: progress } = await getEnrollmentProgress(targetEnrollment.id);
      const lessonUrl = getResumeLessonPath(
        accessibleCourse.sections,
        accessibleCourse.slug || slug,
        progress.completed_lesson_ids ?? [],
      );
      if (!lessonUrl) {
        router.push('/profile#certificates');
        return;
      }
      router.push(lessonUrl);
    } catch (err) {
      console.error('Failed to load enrolled course lessons:', err);
      setEnrollmentError(err instanceof Error ? err.message : 'You’re enrolled, but your next lesson could not be loaded. Please try again.');
    } finally {
      setOpeningLesson(false);
    }
  }, [enrollment, router, slug]);

  const enrollInCourse = React.useCallback(async (targetCourse: any) => {
    setEnrollmentError(null);
    setEnrolling(true);
    try {
      const { data: enrollmentsData } = await getMyEnrollments();
      const existingEnrollment = (enrollmentsData.results ?? enrollmentsData)
        .find((item: any) => item.course === targetCourse.id);
      if (existingEnrollment) {
        setEnrollment(existingEnrollment);
        await continueLearning(targetCourse, existingEnrollment);
        return;
      }

      const { data } = await enroll(targetCourse.id);
      setEnrollment(data);
      await continueLearning(targetCourse, data);
    } catch (err: any) {
      console.error('Failed to enroll in course:', err);
      setEnrollmentError(
        err?.response?.data?.detail || 'We could not enroll you right now. Please try again.',
      );
    } finally {
      setEnrolling(false);
    }
  }, [continueLearning]);

  useEffect(() => {
    if (
      searchParams.get('enroll') !== '1'
      || !isBackendAuthenticated
      || !course?.id
      || autoEnrollCourseId.current === course.id
    ) {
      return;
    }

    autoEnrollCourseId.current = course.id;
    router.replace(`/courses/${course.slug || slug}?id=${course.id}`);
    void enrollInCourse(course);
  }, [course, enrollInCourse, isBackendAuthenticated, router, searchParams, slug]);

  async function load(forceRefresh = false) {
    try {
      const idParam = searchParams?.get('id');
      if (idParam) {
        try {
          const { data: detail } = await getCourse(idParam, forceRefresh);
          setCourse(detail);
          if (isBackendAuthenticated) {
            try {
              const my = await getMyEnrollments();
              const existing = (my.data.results ?? my.data).find((e: any) => e.course === detail.id);
              setEnrollment(existing ?? null);
            } catch (enrollmentErr) {
              console.warn('Failed to fetch enrollment for course detail page:', enrollmentErr);
              setEnrollment(null);
            }
          }
          return;
        } catch (err) {
          console.warn('Failed to load course by id, trying search fallback:', err);
        }
      }

      const { data } = await getCourses({ search: slug });
      const list = data.results ?? data;
      const match = list.find((c: any) => c.slug === slug) ?? list[0];
      if (!match) {
        setCourse(null);
        setCourseError('This course is not available right now.');
        return;
      }

      const { data: detail } = await getCourse(match.id, forceRefresh);
      setCourse(detail);

      if (isBackendAuthenticated) {
        try {
          const my = await getMyEnrollments();
          const existing = (my.data.results ?? my.data).find((e: any) => e.course === detail.id);
          setEnrollment(existing ?? null);
        } catch (enrollmentErr) {
          console.warn('Failed to fetch enrollment for course detail page:', enrollmentErr);
          setEnrollment(null);
        }
      }
    } catch (err) {
      console.error('Failed to load course detail page:', err);
      setCourse(null);
      setCourseError('Unable to load this course right now. Please try again in a moment.');
    } finally {
      setLoading(false);
    }
  }

  loadRef.current = load;

  async function handleEnroll() {
    if (!course) return;

    const targetSlug = course.slug || slug;

    if (!isBackendAuthenticated) {
      const authReturnTo = `/courses/${targetSlug}?id=${course.id}&enroll=1`;
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('open-auth-modal', {
          detail: { tab: isAuthenticated ? 'signin' : 'signup', returnTo: authReturnTo },
        }));
      }
      return;
    }

    await enrollInCourse(course);
  }

  if (loading) return <div className="container section"><InnovationLoader label="Loading course" /></div>;

  if (courseError || !course) {
    return (
      <div className="container section">
        <div className="card" style={{ maxWidth: 560, margin: '40px auto', padding: 28 }}>
          <p style={{ fontSize: 12, letterSpacing: 1.2, textTransform: 'uppercase', color: 'var(--brand)', marginBottom: 10 }}>Course unavailable</p>
          <h1 style={{ fontSize: 28, marginBottom: 10 }}>We couldn’t load this course</h1>
          <p style={{ color: 'var(--text-muted)', marginBottom: 20 }}>{courseError || 'This course could not be found.'}</p>
          <button className="btn btn-primary" style={{ marginRight: 10 }} onClick={() => {
            setCourseError(null);
            setLoading(true);
            void loadRef.current(true);
          }}>Try again</button>
          <button className="btn btn-primary" onClick={() => router.push('/courses')}>Browse courses</button>
        </div>
      </div>
    );
  }

  return (
    <div className="container section">
      <div className="course-detail-layout" style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 32 }}>
        <div className="course-action-sidebar">
          <span className="badge" style={{ marginBottom: 12, display: 'inline-block' }}>{course.category_name}</span>
          <h1 style={{ fontSize: 30, margin: '0 0 8px' }}>{course.title}</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 15, marginBottom: 4 }}>{course.subtitle}</p>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, margin: '12px 0 20px' }}>
            {course.instructor_photo ? (
              <ApiImage src={course.instructor_photo} alt={course.instructor_name} width={32} height={32} fallbackSrc="/favicon.svg" style={{ borderRadius: '50%' }} />
            ) : (
              <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'var(--surface-2)' }} />
            )}
            <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>By {course.instructor_name}</span>
          </div>

          <div className="rich-editor-content" dangerouslySetInnerHTML={{ __html: sanitizeRichText(course.description) }} />

          {course.notes_enabled && course.notes && (
            <div className="card course-notes-card" style={{ marginTop: 20, borderColor: 'var(--brand)' }}>
              <p style={{ fontWeight: 600, marginBottom: 8, fontSize: 13, color: 'var(--brand)' }}>Course Notes</p>
              <div className="rich-editor-content" dangerouslySetInnerHTML={{ __html: sanitizeRichText(course.notes) }} />
            </div>
          )}

          <h2 className="course-curriculum-title" style={{ fontSize: 20, margin: '32px 0 16px' }}>Curriculum</h2>
          {weekGroups.map(([key, week], index: number) => {
            const isOpen = openWeeks[key] ?? index === 0;
            return (
            <div key={key} className="card course-section-card" style={{ marginBottom: 14 }}>
              <button
                type="button"
                onClick={() => setOpenWeeks((weeks) => ({ ...weeks, [key]: !isOpen }))}
                aria-expanded={isOpen}
                aria-label={isOpen ? `Minimize ${week.title}` : `Expand ${week.title}`}
                title={isOpen ? 'Minimize lessons' : 'Expand lessons'}
                className="course-section-toggle"
                style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', border: 0, background: 'transparent', color: 'var(--text)', padding: 0, cursor: 'pointer', textAlign: 'left' }}
              >
                <span className="course-section-title" style={{ fontWeight: 600 }}>{week.title}</span>
                <ChevronDown size={18} aria-hidden="true" style={{ transform: isOpen ? 'rotate(0deg)' : 'rotate(-90deg)', transition: 'transform 180ms ease' }} />
              </button>
              {isOpen && <div className="course-section-content" style={{ marginTop: 10 }}>
                {week.sections.map((section: any) => (
                  <div key={section.id}>
                    <p className="course-module-label" style={{ color: 'var(--text-muted)', fontSize: 12, fontWeight: 600, margin: '10px 0 4px' }}>{section.title.replace(/^Week\s+\d+:\s*/i, '')}</p>
                    {section.lessons.map((lesson: any) => {
                      const Icon = ICONS[lesson.lesson_type] ?? BookOpen;
                      const locked = !lesson.is_unlocked;
                      return (
                        <div
                          key={`${section.id}-${lesson.order}-${lesson.title}`}
                          onClick={() => !locked && router.push(`/courses/${slug}/lessons/${lesson.id}`)}
                          onKeyDown={(event) => {
                            if (!locked && (event.key === 'Enter' || event.key === ' ')) {
                              event.preventDefault();
                              router.push(`/courses/${slug}/lessons/${lesson.id}`);
                            }
                          }}
                          role="button"
                          tabIndex={locked ? -1 : 0}
                          className="course-lesson-row"
                          style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 0', borderTop: '1px solid var(--border)', cursor: locked ? 'not-allowed' : 'pointer', opacity: locked ? 0.5 : 1 }}
                        >
                          <Icon size={16} color="var(--text-muted)" />
                          <span className="course-lesson-title" style={{ flex: 1, fontSize: 14 }}>{lesson.title}</span>
                          {locked && <Lock size={14} color="var(--text-muted)" />}
                        </div>
                      );
                    })}
                    {enrollment && moduleFinalQuizzes[String(section.id)] && (
                      <button
                        type="button"
                        className="btn btn-accent course-quiz-button"
                        style={{ width: '100%', marginTop: 10 }}
                        onClick={() => router.push(`/quizzes/${moduleFinalQuizzes[String(section.id)].id}`)}
                      >
                        Take module final quiz
                      </button>
                    )}
                  </div>
                ))}
              </div>}
            </div>
            );
          })}
        </div>

        <div>
          <div className="card">
            <div style={{ height: 160, background: 'var(--surface-2)', borderRadius: 10, marginBottom: 16, position: 'relative', overflow: 'hidden' }}>
              <ApiImage src={course.thumbnail} alt={course.title} fill sizes="(max-width: 900px) 100vw, 280px" style={{ objectFit: 'cover' }} />
            </div>
            <p style={{ fontSize: 24, fontWeight: 700, marginBottom: 12 }}>
              {course.is_free ? 'Free' : `${course.price} ETB`}
            </p>
            {enrollment ? (
              <>
                <p style={{ fontSize: 13, color: 'var(--brand)', marginBottom: 10 }}>✓ You&apos;re enrolled — {enrollment.progress_percent}% complete</p>
                <button className="btn btn-primary course-action-button" style={{ width: '100%', marginBottom: 10 }} disabled={openingLesson} onClick={() => {
                  void continueLearning(course);
                }}>
                  {openingLesson ? 'Opening your lesson...' : 'Continue learning'}
                </button>
                {enrollmentError && <p role="alert" style={{ color: 'var(--danger)', fontSize: 13, marginTop: 10 }}>{enrollmentError}</p>}
                <button className="btn course-action-button" style={{ width: '100%' }} onClick={() => router.push(`/ai-tutor?course=${course.id}`)}>
                  Ask the AI Tutor about this course
                </button>
                {finalExam && enrollment.progress_percent >= 100 && (
                  <button
                    className="btn btn-accent course-action-button"
                    style={{ width: '100%', marginTop: 10 }}
                    onClick={() => router.push(`/quizzes/${finalExam.id}`)}
                  >
                    Take final exam
                  </button>
                )}
              </>
            ) : (
              <>
                <button className="btn btn-primary course-action-button" style={{ width: '100%' }} onClick={handleEnroll} disabled={enrolling}>
                  {enrolling ? 'Enrolling...' : course.is_free ? 'Enroll for Free' : 'Enroll Now'}
                </button>
                {enrollmentError && <p role="alert" style={{ color: 'var(--danger)', fontSize: 13, marginTop: 10 }}>{enrollmentError}</p>}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
