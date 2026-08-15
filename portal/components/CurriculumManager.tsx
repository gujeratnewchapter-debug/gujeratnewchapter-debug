'use client';

import React, { useEffect, useState } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { RichTextEditor } from './RichTextEditor';
import * as api from '@/lib/api';

interface ChoiceEdit { id: number; text: string; is_correct: boolean; order: number }
interface QuestionEdit { id: number; text: string; choices: ChoiceEdit[] }
interface QuizEdit { id: number; passing_score_percent: number; questions: QuestionEdit[] }
interface LessonEdit {
  id: number; title: string; lesson_type: string; order: number;
  video_url: string; content_text: string; quiz: QuizEdit | null;
}
interface SectionEdit { id: number; title: string; order: number; lessons: LessonEdit[] }

export function CurriculumManager({ courseId, initialSections }: { courseId: number; initialSections: any[] }) {
  const [sections, setSections] = useState<SectionEdit[] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAll();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function loadAll() {
    setLoading(true);
    const built: SectionEdit[] = [];
    for (const s of initialSections) {
      const lessons: LessonEdit[] = [];
      for (const l of s.lessons) {
        const { data: fullLesson } = await api.getLesson(l.id);
        let quiz: QuizEdit | null = null;
        try {
          const { data: quizList } = await api.getQuizzesForLesson(l.id);
          const quizRows = quizList.results ?? quizList;
          if (quizRows.length > 0) {
            const q = quizRows[0];
            quiz = {
              id: q.id, passing_score_percent: q.passing_score_percent,
              questions: (q.questions ?? []).map((qq: any) => ({
                id: qq.id, text: qq.text,
                choices: (qq.choices ?? []).map((c: any) => ({ id: c.id, text: c.text, is_correct: c.is_correct, order: c.order })),
              })),
            };
          }
        } catch (err) {
          console.error('Failed to load quiz for lesson', l.id, err);
        }
        lessons.push({
          id: fullLesson.id, title: fullLesson.title, lesson_type: fullLesson.lesson_type, order: fullLesson.order,
          video_url: fullLesson.video_url || '', content_text: fullLesson.content_text || '', quiz,
        });
      }
      built.push({ id: s.id, title: s.title, order: s.order, lessons });
    }
    setSections(built);
    setLoading(false);
  }

  function patchSection(id: number, patch: Partial<SectionEdit>) {
    setSections((prev) => prev!.map((s) => (s.id === id ? { ...s, ...patch } : s)));
  }
  function patchLesson(sectionId: number, lessonId: number, patch: Partial<LessonEdit>) {
    setSections((prev) => prev!.map((s) => s.id !== sectionId ? s : {
      ...s, lessons: s.lessons.map((l) => (l.id === lessonId ? { ...l, ...patch } : l)),
    }));
  }

  async function addSection() {
    const order = (sections?.length ?? 0) + 1;
    const { data } = await api.createSection({ course: courseId, title: `Module ${order}`, order });
    setSections((prev) => [...(prev ?? []), { id: data.id, title: data.title, order: data.order, lessons: [] }]);
  }

  async function deleteSection(id: number) {
    if (!confirm('Delete this entire module and its lessons?')) return;
    await api.deleteSection(id);
    setSections((prev) => prev!.filter((s) => s.id !== id));
  }

  async function addLesson(sectionId: number) {
    const section = sections!.find((s) => s.id === sectionId)!;
    const order = section.lessons.length + 1;
    const { data } = await api.createLesson({ section: sectionId, title: `Lesson ${order}`, lesson_type: 'text', order, content_text: '' });
    patchSection(sectionId, { lessons: [...section.lessons, { id: data.id, title: data.title, lesson_type: data.lesson_type, order: data.order, video_url: '', content_text: '', quiz: null }] });
  }

  async function deleteLesson(sectionId: number, lessonId: number) {
    if (!confirm('Delete this lesson?')) return;
    await api.deleteLesson(lessonId);
    const section = sections!.find((s) => s.id === sectionId)!;
    patchSection(sectionId, { lessons: section.lessons.filter((l) => l.id !== lessonId) });
  }

  async function enableQuiz(sectionId: number, lesson: LessonEdit) {
    const { data } = await api.createQuiz({ course: courseId, lesson: lesson.id, title: `${lesson.title} Quiz`, passing_score_percent: 80 });
    patchLesson(sectionId, lesson.id, { quiz: { id: data.id, passing_score_percent: 80, questions: [] } });
  }

  async function removeQuiz(sectionId: number, lesson: LessonEdit) {
    if (!lesson.quiz) return;
    if (!confirm('Remove this quiz? Students will no longer need to pass it to unlock the next lesson.')) return;
    await api.deleteQuiz(lesson.quiz.id);
    patchLesson(sectionId, lesson.id, { quiz: null });
  }

  async function addQuestion(sectionId: number, lesson: LessonEdit) {
    if (!lesson.quiz) return;
    const { data: q } = await api.createQuestion({ quiz: lesson.quiz.id, text: '', question_type: 'multiple_choice', order: lesson.quiz.questions.length, points: 1 });
    const { data: c1 } = await api.createChoice({ question: q.id, text: '', is_correct: true, order: 0 });
    const { data: c2 } = await api.createChoice({ question: q.id, text: '', is_correct: false, order: 1 });
    patchLesson(sectionId, lesson.id, {
      quiz: { ...lesson.quiz, questions: [...lesson.quiz.questions, { id: q.id, text: '', choices: [
        { id: c1.id, text: '', is_correct: true, order: 0 }, { id: c2.id, text: '', is_correct: false, order: 1 },
      ] }] },
    });
  }

  async function deleteQuestionRow(sectionId: number, lesson: LessonEdit, questionId: number) {
    if (!lesson.quiz) return;
    await api.deleteQuestion(questionId);
    patchLesson(sectionId, lesson.id, { quiz: { ...lesson.quiz, questions: lesson.quiz.questions.filter((q) => q.id !== questionId) } });
  }

  async function setCorrectChoice(sectionId: number, lesson: LessonEdit, question: QuestionEdit, choiceId: number) {
    if (!lesson.quiz) return;
    await Promise.all(question.choices.map((c) => api.updateChoice(c.id, { is_correct: c.id === choiceId })));
    const updatedQuestions = lesson.quiz.questions.map((q) => q.id !== question.id ? q : {
      ...q, choices: q.choices.map((c) => ({ ...c, is_correct: c.id === choiceId })),
    });
    patchLesson(sectionId, lesson.id, { quiz: { ...lesson.quiz, questions: updatedQuestions } });
  }

  async function addChoice(sectionId: number, lesson: LessonEdit, question: QuestionEdit) {
    if (!lesson.quiz) return;
    const { data: c } = await api.createChoice({ question: question.id, text: '', is_correct: false, order: question.choices.length });
    const updatedQuestions = lesson.quiz.questions.map((q) => q.id !== question.id ? q : { ...q, choices: [...q.choices, { id: c.id, text: '', is_correct: false, order: q.choices.length }] });
    patchLesson(sectionId, lesson.id, { quiz: { ...lesson.quiz, questions: updatedQuestions } });
  }

  if (loading || !sections) return <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Loading curriculum...</p>;

  return (
    <div>
      <h2 style={{ fontSize: 18, marginBottom: 14 }}>Curriculum</h2>
      {sections.map((section) => (
        <div key={section.id} className="card" style={{ marginBottom: 18 }}>
          <div style={{ display: 'flex', gap: 10, marginBottom: 12 }}>
            <input
              className="input" style={{ fontWeight: 600 }} value={section.title}
              onChange={(e) => patchSection(section.id, { title: e.target.value })}
              onBlur={() => api.updateSection(section.id, { title: section.title })}
            />
            <button type="button" className="btn" onClick={() => deleteSection(section.id)}><Trash2 size={14} /></button>
          </div>

          {section.lessons.map((lesson) => (
            <div key={lesson.id} style={{ border: '1px solid var(--border)', borderRadius: 10, padding: 14, marginBottom: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <input
                  className="input" style={{ fontWeight: 500, flex: 1, marginRight: 8 }} value={lesson.title}
                  onChange={(e) => patchLesson(section.id, lesson.id, { title: e.target.value })}
                  onBlur={() => api.updateLesson(lesson.id, { title: lesson.title })}
                />
                <button type="button" className="btn" onClick={() => deleteLesson(section.id, lesson.id)}><Trash2 size={14} /></button>
              </div>

              <select
                className="input" style={{ marginBottom: 8 }} value={lesson.lesson_type}
                onChange={(e) => { patchLesson(section.id, lesson.id, { lesson_type: e.target.value }); api.updateLesson(lesson.id, { lesson_type: e.target.value }); }}
              >
                <option value="video">Video</option>
                <option value="text">Text</option>
                <option value="pdf">PDF</option>
                <option value="powerpoint">Slides (PowerPoint)</option>
                <option value="audio">Audio</option>
              </select>

              {lesson.lesson_type === 'video' && (
                <input
                  className="input" placeholder="Video URL" style={{ marginBottom: 8 }} value={lesson.video_url}
                  onChange={(e) => patchLesson(section.id, lesson.id, { video_url: e.target.value })}
                  onBlur={() => api.updateLesson(lesson.id, { video_url: lesson.video_url })}
                />
              )}

              {lesson.lesson_type === 'text' && (
                <div style={{ marginBottom: 8 }}>
                  <RichTextEditor
                    value={lesson.content_text}
                    onChange={(html) => { patchLesson(section.id, lesson.id, { content_text: html }); api.updateLesson(lesson.id, { content_text: html }); }}
                  />
                </div>
              )}

              <div style={{ marginTop: 10 }}>
                {!lesson.quiz ? (
                  <button type="button" className="btn" onClick={() => enableQuiz(section.id, lesson)}>
                    <Plus size={13} /> Add a quiz to gate the next lesson
                  </button>
                ) : (
                  <div style={{ background: 'var(--surface-2)', borderRadius: 8, padding: 12 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                      <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0 }}>
                        {lesson.quiz.questions.length} question{lesson.quiz.questions.length !== 1 ? 's' : ''} · each worth {lesson.quiz.questions.length ? (100 / lesson.quiz.questions.length).toFixed(0) : 0}% · pass at {lesson.quiz.passing_score_percent}%
                      </p>
                      <button type="button" className="btn" style={{ fontSize: 12, color: 'var(--danger)' }} onClick={() => removeQuiz(section.id, lesson)}>Remove quiz</button>
                    </div>

                    {lesson.quiz.questions.map((q, qIdx) => (
                      <div key={q.id} style={{ marginBottom: 10, background: 'var(--surface)', borderRadius: 8, padding: 10 }}>
                        <div style={{ display: 'flex', gap: 8, marginBottom: 6 }}>
                          <input
                            className="input" placeholder={`Question ${qIdx + 1}`} value={q.text}
                            onChange={(e) => {
                              const updated = lesson.quiz!.questions.map((qq) => qq.id === q.id ? { ...qq, text: e.target.value } : qq);
                              patchLesson(section.id, lesson.id, { quiz: { ...lesson.quiz!, questions: updated } });
                            }}
                            onBlur={() => api.updateQuestion(q.id, { text: q.text })}
                          />
                          <button type="button" className="btn" style={{ padding: '6px 10px' }} onClick={() => deleteQuestionRow(section.id, lesson, q.id)}><Trash2 size={12} /></button>
                        </div>
                        {q.choices.map((c) => (
                          <label key={c.id} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, fontSize: 13 }}>
                            <input type="radio" checked={c.is_correct} onChange={() => setCorrectChoice(section.id, lesson, q, c.id)} />
                            <input
                              className="input" style={{ padding: '6px 10px' }} placeholder="Answer option" value={c.text}
                              onChange={(e) => {
                                const updatedChoices = q.choices.map((cc) => cc.id === c.id ? { ...cc, text: e.target.value } : cc);
                                const updatedQuestions = lesson.quiz!.questions.map((qq) => qq.id === q.id ? { ...qq, choices: updatedChoices } : qq);
                                patchLesson(section.id, lesson.id, { quiz: { ...lesson.quiz!, questions: updatedQuestions } });
                              }}
                              onBlur={() => api.updateChoice(c.id, { text: c.text })}
                            />
                          </label>
                        ))}
                        <button type="button" className="btn" style={{ fontSize: 12, marginTop: 4 }} onClick={() => addChoice(section.id, lesson, q)}>+ Add option</button>
                      </div>
                    ))}
                    <button type="button" className="btn" style={{ fontSize: 12 }} onClick={() => addQuestion(section.id, lesson)}>
                      <Plus size={12} /> Add question ({lesson.quiz.questions.length}/10 suggested)
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}

          <button type="button" className="btn" onClick={() => addLesson(section.id)}>
            <Plus size={14} /> Add another lesson to this module
          </button>
        </div>
      ))}

      <button type="button" className="btn" onClick={addSection}>
        <Plus size={14} /> Add another module
      </button>
    </div>
  );
}
