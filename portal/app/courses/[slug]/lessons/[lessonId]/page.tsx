'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ChevronDown } from 'lucide-react';
import { getCourses, getCourse, getLesson, getMyEnrollments, getMyCertificates, getEnrollmentProgress, markLessonComplete, getSection, getQuizzesForLesson, getQuizzesForCourse } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';
import { InnovationLoader } from '@/components/InnovationLoader';
import { sanitizeRichText } from '@/lib/sanitize-html';

export default function LessonPage() {
  const { slug, lessonId } = useParams<{ slug: string; lessonId: string }>();
  const router = useRouter();
  const { isBackendAuthenticated } = useAuth();
  const [lesson, setLesson] = useState<any>(null);
  const [course, setCourse] = useState<any>(null);
  const [enrollment, setEnrollment] = useState<any>(null);
  const [quizId, setQuizId] = useState<number | null>(null);
  const [completing, setCompleting] = useState(false);
  const [completionError, setCompletionError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [syllabusOpen, setSyllabusOpen] = useState(true);
  const [completedLessonIds, setCompletedLessonIds] = useState<number[]>([]);
  const [openWeeks, setOpenWeeks] = useState<Record<string, boolean>>({});
  const [moduleFinalQuizzes, setModuleFinalQuizzes] = useState<Record<string, any>>({});
  const [courseCertificate, setCourseCertificate] = useState<any>(null);

  const allLessons = useMemo(
    () => course?.sections?.flatMap((section: any) => section.lessons ?? []) ?? [],
    [course],
  );
  const currentLessonIndex = allLessons.findIndex((item: any) => item.id === Number(lessonId));
  const nextLesson = allLessons[currentLessonIndex + 1] ?? null;
  const currentSection = useMemo(
    () => course?.sections?.find((section: any) => section.lessons?.some((item: any) => item.id === Number(lessonId))) ?? null,
    [course, lessonId],
  );
  const currentModuleFinalQuiz = currentSection ? moduleFinalQuizzes[String(currentSection.id)] : null;
  const isLastLessonInSection = Boolean(
    currentSection?.lessons?.length && currentSection.lessons[currentSection.lessons.length - 1].id === Number(lessonId),
  );
  const weekGroups = useMemo(() => {
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
    const currentWeek = course?.sections?.find((section: any) =>
      section.lessons?.some((item: any) => item.id === Number(lessonId)),
    );
    const currentTitle = String(currentWeek?.title ?? '');
    const weekNumber = currentTitle.match(/Week\s+(\d+)/i)?.[1];
    const moduleNumber = currentTitle.match(/Module\s+(\d+)/i)?.[1];
    if (weekNumber) setOpenWeeks({ [`week-${weekNumber}`]: true });
    if (moduleNumber) setOpenWeeks({ [`module-${moduleNumber}`]: true });
  }, [course, lessonId]);
  const completedCount = completedLessonIds.length;
  const courseProgress = enrollment ? enrollment.progress_percent : allLessons.length ? Math.round((completedCount / allLessons.length) * 100) : 0;
  const lessonNumber = currentLessonIndex >= 0 ? currentLessonIndex + 1 : 1;
  const lessonProgress = allLessons.length ? Math.round((lessonNumber / allLessons.length) * 100) : 0;

  useEffect(() => {
    load();
  }, [lessonId]);

  async function load() {
    try {
      const courseSearch = await getCourses({ search: slug });
      const courseMatches = courseSearch.data.results ?? courseSearch.data;
      const currentCourse = courseMatches.find((item: any) => item.slug === slug) ?? courseMatches[0];
      if (!currentCourse) {
        setLoadError(true);
        router.replace('/courses');
        return;
      }
      const currentCourseDetail = (await getCourse(currentCourse.id)).data;
      const currentLesson = currentCourseDetail.sections?.flatMap((section: any) => section.lessons ?? [])
        .find((item: any) => item.id === Number(lessonId));
      if (!currentLesson) {
        setLoadError(true);
        router.replace(`/courses/${slug}`);
        return;
      }
      const { data } = await getLesson(Number(lessonId));
      setLesson(data);

      const sectionRes = await getSection(data.section);
      const sectionData = sectionRes.data;
      const courseId = sectionData.course;

      try {
        const courseRes = await getCourse(courseId);
        setCourse(courseRes.data);
        try {
          const quizzesRes = await getQuizzesForCourse(courseId);
          const quizzes = quizzesRes.data.results ?? quizzesRes.data;
          setModuleFinalQuizzes(
            quizzes.reduce((acc: Record<string, any>, quiz: any) => {
              if (quiz.is_final_exam && quiz.section && !quiz.lesson) {
                acc[String(quiz.section)] = quiz;
              }
              return acc;
            }, {}),
          );
        } catch (quizErr) {
          console.warn('Failed to load module final quizzes:', quizErr);
          setModuleFinalQuizzes({});
        }
      } catch (err) {
        console.warn('Failed to load course for lesson sidebar:', err);
      }

      try {
        if (isBackendAuthenticated) {
          try {
            const certificatesRes = await getMyCertificates();
            const certificates = certificatesRes.data.results ?? certificatesRes.data;
            setCourseCertificate(certificates.find((item: any) => item.course === courseId) ?? null);
          } catch (certificateErr) {
            console.warn('Failed to load course certificate:', certificateErr);
          }
          const my = await getMyEnrollments();
          const list = my.data.results ?? my.data;
          const match = list.find((e: any) => e.course === courseId);
            if (match) {
              setEnrollment(match);
              try {
                const progressRes = await getEnrollmentProgress(match.id);
                setCompletedLessonIds(progressRes.data.completed_lesson_ids ?? []);
              } catch (progressErr) {
                console.warn('Failed to fetch lesson progress:', progressErr);
              }
            }
        }
      } catch (err) {
        console.warn('Failed to load enrollment for lesson page:', err);
      }

      try {
        const res = await getQuizzesForLesson(Number(lessonId));
        const qdata = res.data.results ?? res.data;
        if (qdata.length) setQuizId(qdata[0].id);
      } catch (err) {
        console.error('Failed to load quizzes for lesson', lessonId, err);
      }
    } catch (err) {
      console.warn('Lesson link is stale or unavailable:', lessonId, err);
      setLoadError(true);
      router.replace(`/courses/${slug}`);
    }
  }

  async function handleComplete() {
    if (!enrollment) return;
    setCompleting(true);
    setCompletionError(null);
    try {
      await markLessonComplete(enrollment.id, Number(lessonId));
      setCompletedLessonIds((ids) => ids.includes(Number(lessonId)) ? ids : [...ids, Number(lessonId)]);
      if (isLastLessonInSection && currentModuleFinalQuiz) {
        router.push(`/quizzes/${currentModuleFinalQuiz.id}`);
        return;
      }
      if (nextLesson?.id) {
        router.push(`/courses/${slug}/lessons/${nextLesson.id}`);
      } else {
        router.push(`/courses/${slug}`);
      }
    } catch (error: any) {
      setCompletionError(error?.response?.data?.detail || 'This lesson is still locked. Complete the previous lesson and required quiz first.');
    } finally {
      setCompleting(false);
    }
  }

  function getFileExtension(url: string) {
    return url.split('?')[0].split('.').pop()?.toLowerCase() || '';
  }

  function getVideoEmbedUrl(videoUrl: string) {
    try {
      const parsed = new URL(videoUrl);
      const host = parsed.hostname.toLowerCase();
      if (host.includes('youtube.com')) {
        const videoId = parsed.searchParams.get('v') || parsed.pathname.split('/').filter(Boolean).pop();
        return videoId ? `https://www.youtube.com/embed/${videoId}` : videoUrl;
      }
      if (host === 'youtu.be') {
        const videoId = parsed.pathname.split('/').filter(Boolean)[0];
        return videoId ? `https://www.youtube.com/embed/${videoId}` : videoUrl;
      }
      if (host.includes('vimeo.com')) {
        const videoId = parsed.pathname.split('/').filter(Boolean).pop();
        return videoId ? `https://player.vimeo.com/video/${videoId}` : videoUrl;
      }
      return null;
    } catch {
      return null;
    }
  }

  function renderVideoUrl() {
    if (!lesson.video_url) return null;
    const embedUrl = getVideoEmbedUrl(lesson.video_url);
    const extension = getFileExtension(lesson.video_url);

    const videoContent = !embedUrl && ['mp4', 'webm', 'ogg', 'mov', 'm4v'].includes(extension) ? (
      <video
        controls
        controlsList="nodownload"
        disablePictureInPicture
        onContextMenu={(event) => event.preventDefault()}
        src={lesson.video_url}
        style={{ width: '100%', maxHeight: 620, display: 'block', borderRadius: 10, background: '#000' }}
      />
    ) : (
      <div style={{ position: 'relative', paddingBottom: '56.25%', height: 0 }}>
        <iframe
          src={embedUrl || lesson.video_url}
          title={lesson.title}
          style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', border: 0, borderRadius: 10 }}
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
        />
      </div>
    );

    return (
      <section className="lesson-video-panel" aria-label="Lesson video">
        <div className="lesson-video-panel-head">
          <span>Video lesson</span>
          <a href={lesson.video_url} target="_blank" rel="noreferrer">Watch on YouTube</a>
        </div>
        {videoContent}
      </section>
    );
  }

  function renderLessonFile() {
    const fileUrl = lesson.file || lesson.source_url;
    if (!fileUrl) return null;

    const extension = getFileExtension(fileUrl);
    const isPdf = extension === 'pdf' || lesson.lesson_type === 'pdf';
    const isVideo = ['mp4', 'webm', 'ogg', 'mov'].includes(extension);
    const isAudio = ['mp3', 'wav', 'm4a', 'aac', 'ogg'].includes(extension) || lesson.lesson_type === 'audio';

    return (
      <div style={{ marginBottom: 20 }}>
        {isVideo && (
          <video
            controls
            controlsList="nodownload"
            disablePictureInPicture
            onContextMenu={(event) => event.preventDefault()}
            style={{ width: '100%', maxHeight: 560, borderRadius: 12, background: '#000', marginBottom: 12 }}
          >
            <source src={fileUrl} />
          </video>
        )}
        {isAudio && !isVideo && <audio controls src={fileUrl} style={{ width: '100%', marginBottom: 12 }} />}
        {isPdf && (
          <iframe
            src={fileUrl}
            title={`${lesson.title} PDF`}
            style={{ width: '100%', height: 680, border: '1px solid var(--border)', borderRadius: 12, marginBottom: 12 }}
          />
        )}
        {!isVideo && lesson.lesson_type !== 'text' && <a href={fileUrl} target="_blank" rel="noreferrer" className="btn btn-primary" style={{ display: 'inline-flex' }}>
          Open or download {lesson.lesson_type === 'text' ? 'lesson file' : lesson.lesson_type.toUpperCase()}
        </a>}
      </div>
    );
  }

  function renderSupplementaryVideoLink() {
    if (!lesson.source_url) return null;
    return <p style={{ marginBottom: 20 }}><a href={lesson.source_url} target="_blank" rel="noreferrer" className="btn btn-accent">Open supplementary video curriculum</a></p>;
  }

  function renderVideoResource(resource: any) {
    const videoUrl = resource.url || resource.file;
    if (!videoUrl) return null;
    const embedUrl = getVideoEmbedUrl(videoUrl);
    const extension = getFileExtension(videoUrl);
    const isDirectVideo = !embedUrl && ['mp4', 'webm', 'ogg', 'mov', 'm4v'].includes(extension);

    return (
      <div key={resource.id} style={{ marginBottom: 20 }}>
        <p style={{ fontWeight: 600, margin: '0 0 8px' }}>{resource.title}</p>
        {isDirectVideo ? (
          <video controls controlsList="nodownload" disablePictureInPicture src={videoUrl} style={{ width: '100%', maxHeight: 620, borderRadius: 12, background: '#000' }} />
        ) : (
          <div style={{ position: 'relative', paddingBottom: '56.25%', height: 0 }}>
            <iframe src={embedUrl || videoUrl} title={resource.title} allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowFullScreen style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', border: 0, borderRadius: 12 }} />
          </div>
        )}
      </div>
    );
  }

  if (loadError) return <div className="container section">Redirecting to the course...</div>;
  if (!lesson) return <div className="container section"><InnovationLoader label="Loading lesson" /></div>;

  return (
    <div className="container section lesson-page" style={{ maxWidth: 1100 }}>
      <button className="btn" onClick={() => router.push(`/courses/${slug}`)} style={{ marginBottom: 16 }}>← Back to course</button>

      <div className="lesson-layout" style={{ display: 'grid', gridTemplateColumns: '280px minmax(0, 1fr)', gap: 24, alignItems: 'start' }}>
        <aside className="card lesson-syllabus-sidebar" style={{ padding: 16, position: 'sticky', top: 90, maxHeight: 'calc(100vh - 120px)', overflowY: 'auto' }}>
          <button
            type="button"
            onClick={() => setSyllabusOpen((open) => !open)}
            aria-expanded={syllabusOpen}
            aria-label={syllabusOpen ? 'Minimize course syllabus' : 'Expand course syllabus'}
            title={syllabusOpen ? 'Minimize course syllabus' : 'Expand course syllabus'}
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', border: 0, background: 'transparent', color: 'var(--text-muted)', padding: 0, cursor: 'pointer', textAlign: 'left' }}
          >
            <span style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: 1.1 }}>Course syllabus</span>
            <ChevronDown size={17} aria-hidden="true" style={{ transform: syllabusOpen ? 'rotate(0deg)' : 'rotate(-90deg)', transition: 'transform 180ms ease' }} />
          </button>
          {syllabusOpen && <div style={{ marginTop: 18 }}>
            <div style={{ marginBottom: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginBottom: 6 }}>
                <strong style={{ fontSize: 13 }}>Course Progress</strong>
                <span style={{ color: 'var(--brand)', fontSize: 13, fontWeight: 700 }}>{courseProgress}%</span>
              </div>
              <div role="progressbar" aria-label="Course progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={courseProgress} style={{ height: 8, overflow: 'hidden', borderRadius: 999, background: 'var(--surface-2)' }}>
                <div style={{ width: `${courseProgress}%`, height: '100%', borderRadius: 999, background: 'var(--brand)', transition: 'width 200ms ease' }} />
              </div>
              <p style={{ color: 'var(--text-muted)', fontSize: 11, margin: '7px 0 0' }}>{completedCount} of {allLessons.length} lessons completed</p>
            </div>
            {weekGroups.length ? weekGroups.map(([key, week]) => {
              const isOpen = openWeeks[key] ?? false;
              return (
                <div key={key} style={{ borderTop: '1px solid var(--border)', paddingTop: 10, marginTop: 10 }}>
                  <button
                    type="button"
                    onClick={() => setOpenWeeks({ [key]: !isOpen })}
                    aria-expanded={isOpen}
                    style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', border: 0, background: 'transparent', color: 'var(--text)', padding: '3px 0', cursor: 'pointer', textAlign: 'left', fontWeight: 700 }}
                  >
                    <span>{week.title}</span>
                    <ChevronDown size={16} aria-hidden="true" style={{ transform: isOpen ? 'rotate(0deg)' : 'rotate(-90deg)', transition: 'transform 180ms ease' }} />
                  </button>
                  {isOpen && <div style={{ marginTop: 10 }}>
                    {week.sections.map((section: any) => (
                      <div key={section.id} style={{ marginBottom: 14 }}>
                        <p style={{ fontWeight: 600, margin: '0 0 7px', fontSize: 12, color: 'var(--text-muted)' }}>{section.title.replace(/^Week\s+\d+:\s*/i, '')}</p>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                          {section.lessons?.map((item: any) => {
                            const active = item.id === Number(lessonId);
                            const completed = completedLessonIds.includes(item.id);
                            const locked = item.is_unlocked === false && !item.is_preview;
                            return (
                              <button
                                key={item.id}
                                type="button"
                                onClick={() => !locked && router.push(`/courses/${slug}/lessons/${item.id}`)}
                                disabled={locked}
                                style={{ display: 'flex', alignItems: 'center', gap: 7, textAlign: 'left', border: active ? '1px solid var(--brand)' : '1px solid var(--border)', borderRadius: 10, background: active ? 'rgba(20, 184, 166, 0.08)' : 'transparent', color: active ? 'var(--text)' : 'var(--text-muted)', padding: '8px 10px', cursor: locked ? 'not-allowed' : 'pointer', opacity: locked ? 0.55 : 1, fontWeight: active ? 700 : 500 }}
                              >
                                <span style={{ color: completed ? 'var(--brand)' : 'var(--text-muted)', fontSize: 12 }}>{completed ? '✓' : '○'}</span>
                                <span>{item.title}</span>
                              </button>
                            );
                          })}
                          {moduleFinalQuizzes[String(section.id)] && (
                            <button
                              type="button"
                              onClick={() => router.push(`/quizzes/${moduleFinalQuizzes[String(section.id)].id}`)}
                              style={{ display: 'flex', alignItems: 'center', gap: 7, textAlign: 'left', border: '1px solid var(--accent)', borderRadius: 10, background: 'rgba(245, 158, 11, 0.1)', color: 'var(--text)', padding: '8px 10px', cursor: 'pointer', fontWeight: 700 }}
                            >
                              <span style={{ color: 'var(--accent)', fontSize: 12 }}>?</span>
                              <span>{moduleFinalQuizzes[String(section.id)].title}</span>
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>}
                </div>
              );
            }) : <p style={{ color: 'var(--text-muted)', margin: 0 }}>No lesson list available for this course.</p>}
            <button
              type="button"
              onClick={() => courseCertificate && router.push('/profile#certificates')}
              disabled={!courseCertificate}
              style={{ display: 'flex', alignItems: 'center', gap: 7, width: '100%', marginTop: 14, textAlign: 'left', border: `1px solid ${courseCertificate ? 'var(--brand)' : 'var(--border)'}`, borderRadius: 10, background: courseCertificate ? 'rgba(16, 185, 129, 0.1)' : 'var(--surface-2)', color: courseCertificate ? 'var(--text)' : 'var(--text-muted)', padding: '9px 10px', cursor: courseCertificate ? 'pointer' : 'not-allowed', opacity: courseCertificate ? 1 : 0.7, fontWeight: 700 }}
            >
              <span style={{ color: courseCertificate ? 'var(--brand)' : 'var(--text-muted)', fontSize: 12 }}>{courseCertificate ? '✓' : '○'}</span>
              <span>{courseCertificate ? 'Certificate of completion' : 'Certificate locked until course completion'}</span>
            </button>
          </div>}
        </aside>

        <main className="lesson-main" style={{ minWidth: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, marginBottom: 16, flexWrap: 'wrap' }}>
            <div>
              <p style={{ color: 'var(--text-muted)', fontSize: 12, fontWeight: 700, margin: '0 0 5px', textTransform: 'uppercase', letterSpacing: '.08em' }}>Lesson {lessonNumber} of {allLessons.length}</p>
              <h1 className="lesson-topic-title" style={{ fontSize: 24, margin: 0 }}>{lesson.title}</h1>
            </div>
            <div style={{ minWidth: 180, flex: '0 1 220px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5, fontSize: 12, fontWeight: 700 }}><span>Lesson progress</span><span style={{ color: 'var(--brand)' }}>{lessonProgress}%</span></div>
              <div role="progressbar" aria-label="Lesson progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={lessonProgress} style={{ height: 8, overflow: 'hidden', borderRadius: 999, background: 'var(--surface-2)' }}><div style={{ width: `${lessonProgress}%`, height: '100%', borderRadius: 999, background: 'var(--secondary-teal)' }} /></div>
            </div>
          </div>

          {lesson.video_url && renderVideoUrl()}

          {renderSupplementaryVideoLink()}

          {renderLessonFile()}

          {lesson.resources?.filter((resource: any) => resource.resource_type === 'video' && (resource.url || resource.file) !== lesson.video_url).map(renderVideoResource)}

          {lesson.content_text && (
            <div className="rich-editor-content lesson-content" dangerouslySetInnerHTML={{ __html: sanitizeRichText(lesson.content_text) }} style={{ marginBottom: 20 }} />
          )}

          {lesson.resources?.length > 0 && (
            <div style={{ marginBottom: 20 }}>
              <p style={{ fontWeight: 600, marginBottom: 8 }}>Resources</p>
              {lesson.resources.filter((resource: any) => resource.resource_type !== 'video').map((r: any) => (
                <a key={r.id} href={r.url || r.file} target="_blank" rel="noreferrer" className="btn" style={{ display: 'inline-flex', marginRight: 8, marginBottom: 8 }}>
                  {r.url ? 'Open' : 'Download'}: {r.title}
                </a>
              ))}
            </div>
          )}

          {completionError && (
            <p role="alert" style={{ color: 'var(--danger, #dc2626)', margin: '0 0 12px', fontSize: 13 }}>{completionError}</p>
          )}

          {quizId ? (
            <button className="btn btn-primary" onClick={() => router.push(`/quizzes/${quizId}`)}>
              Take the lesson quiz to continue
            </button>
          ) : (
            <button className="btn btn-primary" onClick={handleComplete} disabled={completing}>
              {completing ? 'Saving...' : isLastLessonInSection && currentModuleFinalQuiz ? 'Take Module Final Quiz' : nextLesson ? 'Next Lesson' : 'Finish Lesson'}
            </button>
          )}
        </main>
      </div>
    </div>
  );
}
