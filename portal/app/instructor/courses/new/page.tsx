'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Plus, Trash2, Upload } from 'lucide-react';
import { useAuth } from '@/lib/auth-context';
import { RichTextEditor } from '@/components/RichTextEditor';
import {
  getCategories, createCourse, updateCourse, createSection, createLesson,
  createQuiz, createQuestion, createChoice, apiClient,
} from '@/lib/api';

type LessonDraft = {
  localId: string;
  title: string;
  lesson_type: 'video' | 'pdf' | 'powerpoint' | 'text' | 'audio';
  video_url: string;
  source_url: string;
  file: File | null;
  content_text: string;
  quizEnabled: boolean;
  passingScore: number;
  questions: { localId: string; text: string; choices: { localId: string; text: string; isCorrect: boolean }[] }[];
};

function newLesson(): LessonDraft {
  return {
    localId: crypto.randomUUID(), title: '', lesson_type: 'video', video_url: '', source_url: '',
    file: null, content_text: '', quizEnabled: false, passingScore: 80, questions: [],
  };
}

function newQuestion() {
  return {
    localId: crypto.randomUUID(), text: '',
    choices: [
      { localId: crypto.randomUUID(), text: '', isCorrect: true },
      { localId: crypto.randomUUID(), text: '', isCorrect: false },
    ],
  };
}

export default function NewCoursePage() {
  const { user, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const [step, setStep] = useState<'course' | 'curriculum'>('course');
  const [categories, setCategories] = useState<any[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [courseId, setCourseId] = useState<number | null>(null);

  const [form, setForm] = useState({
    title: '', subtitle: '', short_description: '', description: '', notes: '',
    notes_enabled: false, category: '', level: 'beginner', price: '0', is_free: true, duration_hours: 1,
  });
  const [thumbnail, setThumbnail] = useState<File | null>(null);
  const [thumbnailPreview, setThumbnailPreview] = useState<string | null>(null);

  const [sectionTitle, setSectionTitle] = useState('');
  const [sections, setSections] = useState<{ localId: string; id?: number; title: string; lessons: LessonDraft[] }[]>([]);

  useEffect(() => {
    if (!isLoading && (!isAuthenticated || !(user?.role === 'instructor' || user?.role === 'super_admin'))) {
      router.push('/');
    }
  }, [isLoading, isAuthenticated, user]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    getCategories().then((res) => setCategories(res.data.results ?? res.data)).catch(() => {});
  }, []);

  function slugify(s: string) {
    return s.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
  }

  function handleThumbnail(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    setThumbnail(file);
    if (file) setThumbnailPreview(URL.createObjectURL(file));
  }

  async function handleCreateCourse(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setSaving(true);
    try {
      const { data } = await createCourse({
        title: form.title,
        slug: slugify(form.title) + '-' + Date.now().toString().slice(-5),
        subtitle: form.subtitle,
        short_description: form.short_description,
        description: form.description,
        notes: form.notes,
        notes_enabled: form.notes_enabled,
        category: form.category || null,
        level: form.level,
        status: 'draft',
        price: form.price,
        is_free: form.is_free,
        duration_hours: form.duration_hours,
      });
      let id = data.id;

      if (thumbnail) {
        const fd = new FormData();
        fd.append('thumbnail', thumbnail);
        await apiClient.patch(`/courses/${id}/`, fd);
      }

      setCourseId(id);
      setSections([{ localId: crypto.randomUUID(), title: 'Module 1', lessons: [newLesson()] }]);
      setStep('curriculum');
    } catch (err: any) {
      setError(err?.response?.data ? JSON.stringify(err.response.data) : 'Could not create course.');
    } finally {
      setSaving(false);
    }
  }

  function addSection() {
    setSections((prev) => [...prev, { localId: crypto.randomUUID(), title: `Module ${prev.length + 1}`, lessons: [newLesson()] }]);
  }

  function addLesson(sectionLocalId: string) {
    setSections((prev) => prev.map((s) => (s.localId === sectionLocalId ? { ...s, lessons: [...s.lessons, newLesson()] } : s)));
  }

  function removeLesson(sectionLocalId: string, lessonLocalId: string) {
    setSections((prev) => prev.map((s) => (s.localId === sectionLocalId ? { ...s, lessons: s.lessons.filter((l) => l.localId !== lessonLocalId) } : s)));
  }

  function updateLessonField(sectionLocalId: string, lessonLocalId: string, patch: Partial<LessonDraft>) {
    setSections((prev) => prev.map((s) => s.localId !== sectionLocalId ? s : {
      ...s,
      lessons: s.lessons.map((l) => (l.localId === lessonLocalId ? { ...l, ...patch } : l)),
    }));
  }

  function addQuestion(sectionLocalId: string, lessonLocalId: string) {
    updateSectionLesson(sectionLocalId, lessonLocalId, (l) => ({ ...l, questions: [...l.questions, newQuestion()] }));
  }

  function updateSectionLesson(sectionLocalId: string, lessonLocalId: string, fn: (l: LessonDraft) => LessonDraft) {
    setSections((prev) => prev.map((s) => s.localId !== sectionLocalId ? s : {
      ...s,
      lessons: s.lessons.map((l) => (l.localId === lessonLocalId ? fn(l) : l)),
    }));
  }

  function updateQuestionText(sectionLocalId: string, lessonLocalId: string, qLocalId: string, text: string) {
    updateSectionLesson(sectionLocalId, lessonLocalId, (l) => ({
      ...l, questions: l.questions.map((q) => (q.localId === qLocalId ? { ...q, text } : q)),
    }));
  }

  function updateChoice(sectionLocalId: string, lessonLocalId: string, qLocalId: string, cLocalId: string, patch: Partial<{ text: string; isCorrect: boolean }>) {
    updateSectionLesson(sectionLocalId, lessonLocalId, (l) => ({
      ...l,
      questions: l.questions.map((q) => q.localId !== qLocalId ? q : {
        ...q,
        choices: q.choices.map((c) => c.localId === cLocalId
          ? { ...c, ...patch }
          : (patch.isCorrect ? { ...c, isCorrect: false } : c)), // single-correct radio behavior
      }),
    }));
  }

  function addChoice(sectionLocalId: string, lessonLocalId: string, qLocalId: string) {
    updateSectionLesson(sectionLocalId, lessonLocalId, (l) => ({
      ...l, questions: l.questions.map((q) => q.localId === qLocalId ? { ...q, choices: [...q.choices, { localId: crypto.randomUUID(), text: '', isCorrect: false }] } : q),
    }));
  }

  async function handleSaveCurriculum() {
    if (!courseId) return;
    setSaving(true);
    setError('');
    try {
      for (const [sIdx, section] of sections.entries()) {
        const { data: sectionData } = await createSection({ course: courseId, title: section.title, order: sIdx + 1 });

        for (const [lIdx, lesson] of section.lessons.entries()) {
          if (!lesson.title.trim()) continue;
          const payload: any = {
            section: sectionData.id, title: lesson.title, lesson_type: lesson.lesson_type, order: lIdx + 1,
            video_url: lesson.video_url, source_url: lesson.source_url, content_text: lesson.content_text,
          };
          const { data: lessonData } = await createLesson(payload);

          if (lesson.file) {
            const fd = new FormData();
            fd.append('file', lesson.file);
            await apiClient.patch(`/lessons/${lessonData.id}/`, fd);
          }

          if (lesson.quizEnabled && lesson.questions.length > 0) {
            const { data: quizData } = await createQuiz({
              course: courseId, lesson: lessonData.id, title: `${lesson.title} Quiz`, passing_score_percent: lesson.passingScore,
            });
            for (const [qIdx, q] of lesson.questions.entries()) {
              if (!q.text.trim()) continue;
              const { data: questionData } = await createQuestion({
                quiz: quizData.id, text: q.text, question_type: 'multiple_choice', order: qIdx, points: 1,
              });
              for (const [cIdx, c] of q.choices.entries()) {
                if (!c.text.trim()) continue;
                await createChoice({ question: questionData.id, text: c.text, is_correct: c.isCorrect, order: cIdx });
              }
            }
          }
        }
      }

      await updateCourse(courseId, { status: 'published' });
      router.push('/dashboard');
    } catch (err: any) {
      setError('Something went wrong saving the curriculum. Your course was created as a draft — you can keep editing it.');
    } finally {
      setSaving(false);
    }
  }

  if (isLoading) return <div className="container section">Loading...</div>;

  return (
    <div className="container section" style={{ maxWidth: 720 }}>
      <h1 style={{ fontSize: 26, marginBottom: 24 }}>{step === 'course' ? 'Create a New Course' : 'Build Your Curriculum'}</h1>
      {error && <p style={{ color: 'var(--danger)', marginBottom: 16 }}>{error}</p>}

      {step === 'course' && (
        <form onSubmit={handleCreateCourse} style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <div>
            <label className="label">Course thumbnail</label>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
              <div style={{ width: 100, height: 70, borderRadius: 8, background: 'var(--surface-2)', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {thumbnailPreview ? <img src={thumbnailPreview} alt="thumbnail" style={{ width: '100%', height: '100%', objectFit: 'cover' }} /> : <Upload size={18} color="var(--text-muted)" />}
              </div>
              <label className="btn" style={{ cursor: 'pointer' }}>
                Upload image
                <input type="file" accept="image/*" onChange={handleThumbnail} style={{ display: 'none' }} />
              </label>
            </div>
          </div>

          <div>
            <label className="label">Course topic (title)</label>
            <input required className="input" value={form.title} onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))} placeholder="e.g. Building Your MVP" />
          </div>

          <div>
            <label className="label">Subtitle</label>
            <input className="input" value={form.subtitle} onChange={(e) => setForm((f) => ({ ...f, subtitle: e.target.value }))} placeholder="e.g. From idea to first users in 6 weeks" />
          </div>

          <div>
            <label className="label">Short description (shown on course cards)</label>
            <input className="input" value={form.short_description} onChange={(e) => setForm((f) => ({ ...f, short_description: e.target.value }))} />
          </div>

          <div>
            <label className="label">Description</label>
            <RichTextEditor value={form.description} onChange={(html) => setForm((f) => ({ ...f, description: html }))} placeholder="Full course description..." />
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label className="label" style={{ marginBottom: 0 }}>Course notes</label>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--text-muted)', cursor: 'pointer' }}>
                <input type="checkbox" checked={form.notes_enabled} onChange={(e) => setForm((f) => ({ ...f, notes_enabled: e.target.checked }))} />
                Show as note card to students
              </label>
            </div>
            <div style={{ marginTop: 8 }}>
              <RichTextEditor value={form.notes} onChange={(html) => setForm((f) => ({ ...f, notes: html }))} placeholder="Optional notes for students..." />
            </div>
          </div>

          <div style={{ display: 'flex', gap: 14 }}>
            <div style={{ flex: 1 }}>
              <label className="label">Category</label>
              <select className="input" value={form.category} onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}>
                <option value="">Select category</option>
                {categories.map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div style={{ flex: 1 }}>
              <label className="label">Level</label>
              <select className="input" value={form.level} onChange={(e) => setForm((f) => ({ ...f, level: e.target.value }))}>
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </div>
          </div>

          <div>
            <label className="label">Instructor</label>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{ width: 36, height: 36, borderRadius: '50%', background: 'var(--surface-2)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, fontWeight: 700 }}>
                {(user?.first_name?.[0] ?? user?.username?.[0] ?? '?').toUpperCase()}
              </div>
              <span style={{ fontSize: 14 }}>{user?.first_name} {user?.last_name}</span>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>(edit photo/name from your Profile)</span>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 14, alignItems: 'flex-end' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
              <input type="checkbox" checked={form.is_free} onChange={(e) => setForm((f) => ({ ...f, is_free: e.target.checked }))} />
              Free course
            </label>
            {!form.is_free && (
              <div>
                <label className="label">Price (ETB)</label>
                <input className="input" type="number" value={form.price} onChange={(e) => setForm((f) => ({ ...f, price: e.target.value }))} />
              </div>
            )}
          </div>

          <button className="btn btn-primary" type="submit" disabled={saving}>{saving ? 'Saving...' : 'Continue to Curriculum'}</button>
        </form>
      )}

      {step === 'curriculum' && (
        <div>
          {sections.map((section) => (
            <div key={section.localId} className="card" style={{ marginBottom: 20 }}>
              <input
                className="input"
                style={{ fontWeight: 600, marginBottom: 14 }}
                value={section.title}
                onChange={(e) => setSections((prev) => prev.map((s) => s.localId === section.localId ? { ...s, title: e.target.value } : s))}
                placeholder="Topic / Module title"
              />

              {section.lessons.map((lesson, lIdx) => (
                <div key={lesson.localId} style={{ border: '1px solid var(--border)', borderRadius: 10, padding: 14, marginBottom: 12 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
                    <p style={{ fontWeight: 600, fontSize: 13, margin: 0 }}>Lesson {lIdx + 1}</p>
                    {section.lessons.length > 1 && (
                      <button type="button" onClick={() => removeLesson(section.localId, lesson.localId)} style={{ background: 'none', border: 'none', color: 'var(--danger)', cursor: 'pointer' }}>
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>

                  <input
                    className="input" placeholder="Lesson title" style={{ marginBottom: 8 }}
                    value={lesson.title} onChange={(e) => updateLessonField(section.localId, lesson.localId, { title: e.target.value })}
                  />

                  <select
                    className="input" style={{ marginBottom: 8 }}
                    value={lesson.lesson_type}
                    onChange={(e) => updateLessonField(section.localId, lesson.localId, { lesson_type: e.target.value as any })}
                  >
                    <option value="video">Video</option>
                    <option value="text">Text</option>
                    <option value="pdf">PDF</option>
                    <option value="powerpoint">Slides (PowerPoint)</option>
                    <option value="audio">Audio</option>
                  </select>

                  {lesson.lesson_type === 'video' && (
                    <input
                      className="input" placeholder="Video URL (YouTube/Vimeo) or paste upload URL" style={{ marginBottom: 8 }}
                      value={lesson.video_url} onChange={(e) => updateLessonField(section.localId, lesson.localId, { video_url: e.target.value })}
                    />
                  )}

                  {['pdf', 'powerpoint', 'audio'].includes(lesson.lesson_type) && (
                    <>
                      <input
                        className="input" placeholder="Paste a file URL" style={{ marginBottom: 8 }}
                        value={lesson.source_url} onChange={(e) => updateLessonField(section.localId, lesson.localId, { source_url: e.target.value })}
                      />
                      <label className="btn" style={{ cursor: 'pointer', marginBottom: 8, display: 'inline-flex' }}>
                        {lesson.file ? lesson.file.name : 'Or upload a file'}
                        <input type="file" style={{ display: 'none' }} onChange={(e) => updateLessonField(section.localId, lesson.localId, { file: e.target.files?.[0] ?? null })} />
                      </label>
                    </>
                  )}

                  {lesson.lesson_type === 'text' && (
                    <div style={{ marginBottom: 8 }}>
                      <RichTextEditor value={lesson.content_text} onChange={(html) => updateLessonField(section.localId, lesson.localId, { content_text: html })} placeholder="Lesson content..." />
                    </div>
                  )}

                  <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, margin: '10px 0' }}>
                    <input type="checkbox" checked={lesson.quizEnabled} onChange={(e) => updateLessonField(section.localId, lesson.localId, { quizEnabled: e.target.checked, questions: e.target.checked && lesson.questions.length === 0 ? [newQuestion()] : lesson.questions })} />
                    Add a quiz students must pass to unlock the next lesson
                  </label>

                  {lesson.quizEnabled && (
                    <div style={{ background: 'var(--surface-2)', borderRadius: 8, padding: 12 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                        <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0 }}>
                          {lesson.questions.length} question{lesson.questions.length !== 1 ? 's' : ''} · each worth {lesson.questions.length ? (100 / lesson.questions.length).toFixed(0) : 0}%
                        </p>
                        <label style={{ fontSize: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
                          Pass at
                          <input
                            type="number" className="input" style={{ width: 60, padding: '4px 8px' }}
                            value={lesson.passingScore}
                            onChange={(e) => updateLessonField(section.localId, lesson.localId, { passingScore: Number(e.target.value) })}
                          />%
                        </label>
                      </div>

                      {lesson.questions.map((q, qIdx) => (
                        <div key={q.localId} style={{ marginBottom: 10, background: 'var(--surface)', borderRadius: 8, padding: 10 }}>
                          <input
                            className="input" style={{ marginBottom: 6 }} placeholder={`Question ${qIdx + 1}`}
                            value={q.text} onChange={(e) => updateQuestionText(section.localId, lesson.localId, q.localId, e.target.value)}
                          />
                          {q.choices.map((c) => (
                            <label key={c.localId} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, fontSize: 13 }}>
                              <input type="radio" checked={c.isCorrect} onChange={() => updateChoice(section.localId, lesson.localId, q.localId, c.localId, { isCorrect: true })} />
                              <input
                                className="input" style={{ padding: '6px 10px' }} placeholder="Answer option"
                                value={c.text} onChange={(e) => updateChoice(section.localId, lesson.localId, q.localId, c.localId, { text: e.target.value })}
                              />
                            </label>
                          ))}
                          <button type="button" className="btn" style={{ fontSize: 12, padding: '4px 10px', marginTop: 4 }} onClick={() => addChoice(section.localId, lesson.localId, q.localId)}>
                            + Add option
                          </button>
                        </div>
                      ))}
                      <button type="button" className="btn" style={{ fontSize: 12 }} onClick={() => addQuestion(section.localId, lesson.localId)}>
                        <Plus size={12} /> Add question ({lesson.questions.length}/10 suggested)
                      </button>
                    </div>
                  )}
                </div>
              ))}

              <button type="button" className="btn" onClick={() => addLesson(section.localId)}>
                <Plus size={14} /> Add another lesson to this topic
              </button>
            </div>
          ))}

          <button type="button" className="btn" onClick={addSection} style={{ marginBottom: 24 }}>
            <Plus size={14} /> Add another topic/module
          </button>

          <button className="btn btn-primary" style={{ width: '100%' }} onClick={handleSaveCurriculum} disabled={saving}>
            {saving ? 'Publishing...' : 'Save & Publish Course'}
          </button>
        </div>
      )}
    </div>
  );
}
