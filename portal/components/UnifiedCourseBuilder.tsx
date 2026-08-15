'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Copy,
  Eye,
  FileText,
  GripVertical,
  Plus,
  Save,
  Trash2,
  Upload,
} from 'lucide-react';
import { useAuth } from '@/lib/auth-context';
import { RichTextEditor } from '@/components/RichTextEditor';
import * as api from '@/lib/api';

const QUESTION_TYPES = [
  { value: 'multiple_choice', label: 'Multiple Choice' },
  { value: 'checkbox', label: 'Checkbox / Multi-select' },
  { value: 'true_false', label: 'True / False' },
  { value: 'fill_blank', label: 'Fill in the Blank' },
  { value: 'essay', label: 'Essay' },
  { value: 'matching', label: 'Matching' },
  { value: 'ordering', label: 'Ordering' },
];

type QuestionType = typeof QUESTION_TYPES[number]['value'];

type ChoiceDraft = {
  id?: number;
  localId: string;
  text: string;
  is_correct: boolean;
  order: number;
};

type QuestionDraft = {
  id?: number;
  localId: string;
  text: string;
  question_type: QuestionType;
  points: number;
  required: boolean;
  explanation: string;
  choices: ChoiceDraft[];
};

type QuizDraft = {
  id?: number;
  localId: string;
  title: string;
  instructions: string;
  passing_score_percent: number;
  max_attempts: number;
  time_limit_minutes: number;
  randomize_questions: boolean;
  randomize_choices: boolean;
  show_results: boolean;
  show_correct_answers: boolean;
  questions: QuestionDraft[];
};

type LessonDraft = {
  id?: number;
  localId: string;
  title: string;
  slug: string;
  description: string;
  lesson_type: 'text' | 'video' | 'pdf' | 'powerpoint' | 'audio';
  duration_minutes: number;
  content_text: string;
  video_url: string;
  file: File | null;
  is_preview: boolean;
  quiz: QuizDraft | null;
};

type ModuleDraft = {
  id?: number;
  localId: string;
  title: string;
  description: string;
  lessons: LessonDraft[];
};

type CourseDraft = {
  title: string;
  slug: string;
  subtitle: string;
  short_description: string;
  description: string;
  learning_objectives: string;
  requirements: string;
  target_audience: string;
  tags: string;
  category: string;
  level: string;
  status: string;
  language: string;
  duration_hours: number;
  price: string;
  is_free: boolean;
  thumbnail: File | null;
  notes: string;
  notes_enabled: boolean;
};

const createChoice = (text = '', is_correct = false): ChoiceDraft => ({
  localId: crypto.randomUUID(),
  text,
  is_correct,
  order: 0,
});

const createQuestion = (): QuestionDraft => ({
  localId: crypto.randomUUID(),
  text: '',
  question_type: 'multiple_choice',
  points: 1,
  required: true,
  explanation: '',
  choices: [createChoice('Option A', true), createChoice('Option B', false)],
});

const createQuiz = (): QuizDraft => ({
  localId: crypto.randomUUID(),
  title: 'Lesson Quiz',
  instructions: '',
  passing_score_percent: 80,
  max_attempts: 3,
  time_limit_minutes: 0,
  randomize_questions: false,
  randomize_choices: false,
  show_results: true,
  show_correct_answers: true,
  questions: [createQuestion()],
});

const createLesson = (): LessonDraft => ({
  localId: crypto.randomUUID(),
  title: 'New lesson',
  slug: '',
  description: '',
  lesson_type: 'text',
  duration_minutes: 15,
  content_text: '',
  video_url: '',
  file: null,
  is_preview: false,
  quiz: null,
});

const createModule = (): ModuleDraft => ({
  localId: crypto.randomUUID(),
  title: 'Module',
  description: '',
  lessons: [createLesson()],
});

const initialCourse: CourseDraft = {
  title: '',
  slug: '',
  subtitle: '',
  short_description: '',
  description: '',
  learning_objectives: '',
  requirements: '',
  target_audience: '',
  tags: '',
  category: '',
  level: 'beginner',
  status: 'draft',
  language: 'English',
  duration_hours: 1,
  price: '0',
  is_free: true,
  thumbnail: null,
  notes: '',
  notes_enabled: false,
};

function slugify(value: string) {
  return value.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
}

function getQuestionTypeLabel(type: QuestionType) {
  return QUESTION_TYPES.find((item) => item.value === type)?.label ?? 'Question';
}

export function UnifiedCourseBuilder({ mode, courseId: initialCourseId }: { mode: 'new' | 'edit'; courseId?: number }) {
  const router = useRouter();
  const { user, isAuthenticated, isLoading } = useAuth();
  const [categories, setCategories] = useState<any[]>([]);
  const [course, setCourse] = useState<CourseDraft>(initialCourse);
  const [modules, setModules] = useState<ModuleDraft[]>([createModule()]);
  const [courseId, setCourseId] = useState<number | undefined>(initialCourseId);
  const [status, setStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [message, setMessage] = useState<string>('');
  const [activePanel, setActivePanel] = useState<'info' | 'structure' | 'preview'>('info');
  const [thumbnailPreview, setThumbnailPreview] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoading && (!isAuthenticated || !(user?.role === 'instructor' || user?.role === 'super_admin'))) {
      router.push('/');
    }
  }, [isLoading, isAuthenticated, user, router]);

  useEffect(() => {
    async function loadCategories() {
      try {
        const res = await api.getCategories();
        setCategories(res.data.results ?? res.data);
      } catch (err) {
        console.error('Failed to load categories:', err);
      }
    }
    loadCategories();
  }, []);

  useEffect(() => {
    async function loadCourse() {
      if (mode !== 'edit' || !courseId) return;
      try {
        const { data } = await api.getCourse(courseId);
        setCourse({
          title: data.title ?? '',
          slug: data.slug ?? '',
          subtitle: data.subtitle ?? '',
          short_description: data.short_description ?? '',
          description: data.description ?? '',
          learning_objectives: data.learning_objectives ?? '',
          requirements: data.requirements ?? '',
          target_audience: data.target_audience ?? '',
          tags: data.tags ?? '',
          category: data.category ? String(data.category) : '',
          level: data.level ?? 'beginner',
          status: data.status ?? 'draft',
          language: data.language ?? 'English',
          duration_hours: Number(data.duration_hours ?? 1),
          price: String(data.price ?? '0'),
          is_free: !!data.is_free,
          thumbnail: null,
          notes: data.notes ?? '',
          notes_enabled: !!data.notes_enabled,
        });
        setThumbnailPreview(data.thumbnail ?? null);

        const builtModules: ModuleDraft[] = (data.sections ?? []).map((section: any) => ({
          id: section.id,
          localId: crypto.randomUUID(),
          title: section.title ?? 'Module',
          description: '',
          lessons: (section.lessons ?? []).map((lesson: any) => ({
            id: lesson.id,
            localId: crypto.randomUUID(),
            title: lesson.title ?? 'Lesson',
            slug: lesson.slug ?? '',
            description: lesson.description ?? '',
            lesson_type: lesson.lesson_type ?? 'text',
            duration_minutes: Number(lesson.duration_minutes ?? 0),
            content_text: lesson.content_text ?? '',
            video_url: lesson.video_url ?? '',
            file: null,
            is_preview: !!lesson.is_preview,
            quiz: null,
          })),
        }));

        for (const module of builtModules) {
          for (const lesson of module.lessons) {
            if (!lesson.id) continue;
            const quizResult = await api.getQuizzesForLesson(lesson.id);
            const quizData = (quizResult.data.results ?? quizResult.data)?.[0];
            if (!quizData) continue;
            lesson.quiz = {
              id: quizData.id,
              localId: crypto.randomUUID(),
              title: quizData.title ?? 'Lesson Quiz',
              instructions: '',
              passing_score_percent: Number(quizData.passing_score_percent ?? 80),
              max_attempts: Number(quizData.max_attempts ?? 3),
              time_limit_minutes: Number(quizData.time_limit_minutes ?? 0),
              randomize_questions: !!quizData.randomize_questions,
              randomize_choices: false,
              show_results: true,
              show_correct_answers: true,
              questions: (quizData.questions ?? []).map((question: any) => ({
                id: question.id,
                localId: crypto.randomUUID(),
                text: question.text ?? '',
                question_type: question.question_type ?? 'multiple_choice',
                points: Number(question.points ?? 1),
                required: true,
                explanation: '',
                choices: (question.choices ?? []).map((choice: any) => ({
                  id: choice.id,
                  localId: crypto.randomUUID(),
                  text: choice.text ?? '',
                  is_correct: !!choice.is_correct,
                  order: Number(choice.order ?? 0),
                })),
              })),
            };
          }
        }
        setModules(builtModules.length ? builtModules : [createModule()]);
      } catch (err) {
        console.error('Failed to load course builder state:', err);
      }
    }
    loadCourse();
  }, [courseId, mode]);

  const liveCourseSlug = useMemo(() => course.slug || slugify(course.title) || 'course', [course.slug, course.title]);

  function updateCourseField<K extends keyof CourseDraft>(field: K, value: CourseDraft[K]) {
    setCourse((prev) => ({ ...prev, [field]: value }));
  }

  function updateModule(moduleLocalId: string, patch: Partial<ModuleDraft>) {
    setModules((prev) => prev.map((module) => (module.localId === moduleLocalId ? { ...module, ...patch } : module)));
  }

  function updateLesson(moduleLocalId: string, lessonLocalId: string, patch: Partial<LessonDraft>) {
    setModules((prev) => prev.map((module) => (module.localId !== moduleLocalId ? module : {
      ...module,
      lessons: module.lessons.map((lesson) => (lesson.localId === lessonLocalId ? { ...lesson, ...patch } : lesson)),
    })));
  }

  function addModule() {
    setModules((prev) => [...prev, createModule()]);
  }

  function duplicateModule(moduleLocalId: string) {
    setModules((prev) => {
      const index = prev.findIndex((module) => module.localId === moduleLocalId);
      if (index === -1) return prev;
      const clone = {
        ...prev[index],
        localId: crypto.randomUUID(),
        lessons: prev[index].lessons.map((lesson) => ({
          ...lesson,
          localId: crypto.randomUUID(),
          id: undefined,
          quiz: lesson.quiz ? {
            ...lesson.quiz,
            localId: crypto.randomUUID(),
            id: undefined,
            questions: lesson.quiz.questions.map((question) => ({
              ...question,
              localId: crypto.randomUUID(),
              id: undefined,
              choices: question.choices.map((choice) => ({ ...choice, localId: crypto.randomUUID(), id: undefined })),
            })),
          } : null,
        })),
      };
      return [...prev.slice(0, index + 1), clone, ...prev.slice(index + 1)];
    });
  }

  function deleteModule(moduleLocalId: string) {
    setModules((prev) => prev.filter((module) => module.localId !== moduleLocalId));
  }

  function moveModule(direction: 'up' | 'down', moduleLocalId: string) {
    setModules((prev) => {
      const index = prev.findIndex((module) => module.localId === moduleLocalId);
      const nextIndex = direction === 'up' ? index - 1 : index + 1;
      if (index < 0 || nextIndex < 0 || nextIndex >= prev.length) return prev;
      const copied = [...prev];
      [copied[index], copied[nextIndex]] = [copied[nextIndex], copied[index]];
      return copied;
    });
  }

  function addLesson(moduleLocalId: string) {
    setModules((prev) => prev.map((module) => (module.localId === moduleLocalId ? { ...module, lessons: [...module.lessons, createLesson()] } : module)));
  }

  function duplicateLesson(moduleLocalId: string, lessonLocalId: string) {
    setModules((prev) => prev.map((module) => module.localId !== moduleLocalId ? module : {
      ...module,
      lessons: module.lessons.flatMap((lesson) => {
        if (lesson.localId !== lessonLocalId) return [lesson];
        const clone = {
          ...lesson,
          localId: crypto.randomUUID(),
          id: undefined,
          title: `${lesson.title} Copy`,
          slug: '',
          quiz: lesson.quiz ? {
            ...lesson.quiz,
            localId: crypto.randomUUID(),
            id: undefined,
            questions: lesson.quiz.questions.map((question) => ({
              ...question,
              localId: crypto.randomUUID(),
              id: undefined,
              choices: question.choices.map((choice) => ({ ...choice, localId: crypto.randomUUID(), id: undefined })),
            })),
          } : null,
        };
        return [lesson, clone];
      }),
    }));
  }

  function deleteLesson(moduleLocalId: string, lessonLocalId: string) {
    setModules((prev) => prev.map((module) => (module.localId === moduleLocalId ? { ...module, lessons: module.lessons.filter((lesson) => lesson.localId !== lessonLocalId) } : module)));
  }

  function moveLesson(moduleLocalId: string, lessonLocalId: string, direction: 'up' | 'down') {
    setModules((prev) => prev.map((module) => module.localId !== moduleLocalId ? module : {
      ...module,
      lessons: (() => {
        const index = module.lessons.findIndex((lesson) => lesson.localId === lessonLocalId);
        const target = direction === 'up' ? index - 1 : index + 1;
        if (index < 0 || target < 0 || target >= module.lessons.length) return module.lessons;
        const copied = [...module.lessons];
        [copied[index], copied[target]] = [copied[target], copied[index]];
        return copied;
      })(),
    }));
  }

  function ensureQuiz(moduleLocalId: string, lessonLocalId: string) {
    updateLesson(moduleLocalId, lessonLocalId, {
      quiz: createQuiz(),
    });
  }

  function removeQuiz(moduleLocalId: string, lessonLocalId: string) {
    updateLesson(moduleLocalId, lessonLocalId, { quiz: null });
  }

  function addQuestion(moduleLocalId: string, lessonLocalId: string) {
    setModules((prev) => prev.map((module) => (module.localId !== moduleLocalId ? module : {
      ...module,
      lessons: module.lessons.map((lesson) => (lesson.localId !== lessonLocalId ? lesson : {
        ...lesson,
        quiz: lesson.quiz ? { ...lesson.quiz, questions: [...lesson.quiz.questions, createQuestion()] } : lesson.quiz,
      })),
    })));
  }

  function duplicateQuestion(moduleLocalId: string, lessonLocalId: string, questionLocalId: string) {
    setModules((prev) => prev.map((module) => module.localId !== moduleLocalId ? module : {
      ...module,
      lessons: module.lessons.map((lesson) => lesson.localId !== lessonLocalId ? lesson : {
        ...lesson,
        quiz: lesson.quiz ? {
          ...lesson.quiz,
          questions: lesson.quiz.questions.flatMap((question) => {
            if (question.localId !== questionLocalId) return [question];
            const clone = {
              ...question,
              localId: crypto.randomUUID(),
              id: undefined,
              text: `${question.text || 'Question'} Copy`,
              choices: question.choices.map((choice) => ({ ...choice, localId: crypto.randomUUID(), id: undefined })),
            };
            return [question, clone];
          }),
        } : null,
      }),
    }));
  }

  function deleteQuestion(moduleLocalId: string, lessonLocalId: string, questionLocalId: string) {
    setModules((prev) => prev.map((module) => module.localId !== moduleLocalId ? module : {
      ...module,
      lessons: module.lessons.map((lesson) => lesson.localId !== lessonLocalId ? lesson : {
        ...lesson,
        quiz: lesson.quiz ? { ...lesson.quiz, questions: lesson.quiz.questions.filter((question) => question.localId !== questionLocalId) } : null,
      }),
    }));
  }

  function moveQuestion(moduleLocalId: string, lessonLocalId: string, questionLocalId: string, direction: 'up' | 'down') {
    setModules((prev) => prev.map((module) => module.localId !== moduleLocalId ? module : {
      ...module,
      lessons: module.lessons.map((lesson) => lesson.localId !== lessonLocalId ? lesson : {
        ...lesson,
        quiz: lesson.quiz ? { ...lesson.quiz, questions: (() => {
          const index = lesson.quiz.questions.findIndex((question) => question.localId === questionLocalId);
          const target = direction === 'up' ? index - 1 : index + 1;
          if (index < 0 || target < 0 || target >= lesson.quiz.questions.length) return lesson.quiz.questions;
          const copied = [...lesson.quiz.questions];
          [copied[index], copied[target]] = [copied[target], copied[index]];
          return copied;
        })() } : null,
      }),
    }));
  }

  function addChoice(moduleLocalId: string, lessonLocalId: string, questionLocalId: string) {
    setModules((prev) => prev.map((module) => module.localId !== moduleLocalId ? module : {
      ...module,
      lessons: module.lessons.map((lesson) => lesson.localId !== lessonLocalId ? lesson : {
        ...lesson,
        quiz: lesson.quiz ? { ...lesson.quiz, questions: lesson.quiz.questions.map((question) => question.localId !== questionLocalId ? question : {
          ...question,
          choices: [...question.choices, createChoice('', false)],
        }) } : null,
      }),
    }));
  }

  function updateQuestion(moduleLocalId: string, lessonLocalId: string, questionLocalId: string, patch: Partial<QuestionDraft>) {
    setModules((prev) => prev.map((module) => module.localId !== moduleLocalId ? module : {
      ...module,
      lessons: module.lessons.map((lesson) => lesson.localId !== lessonLocalId ? lesson : {
        ...lesson,
        quiz: lesson.quiz ? { ...lesson.quiz, questions: lesson.quiz.questions.map((question) => question.localId === questionLocalId ? { ...question, ...patch } : question) } : null,
      }),
    }));
  }

  function updateChoice(moduleLocalId: string, lessonLocalId: string, questionLocalId: string, choiceLocalId: string, patch: Partial<ChoiceDraft>) {
    setModules((prev) => prev.map((module) => module.localId !== moduleLocalId ? module : {
      ...module,
      lessons: module.lessons.map((lesson) => lesson.localId !== lessonLocalId ? lesson : {
        ...lesson,
        quiz: lesson.quiz ? { ...lesson.quiz, questions: lesson.quiz.questions.map((question) => question.localId !== questionLocalId ? question : {
          ...question,
          choices: question.choices.map((choice) => choice.localId === choiceLocalId ? { ...choice, ...patch } : patch.is_correct ? { ...choice, is_correct: false } : choice),
        }) } : null,
      }),
    }));
  }

  function deleteChoice(moduleLocalId: string, lessonLocalId: string, questionLocalId: string, choiceLocalId: string) {
    setModules((prev) => prev.map((module) => module.localId !== moduleLocalId ? module : {
      ...module,
      lessons: module.lessons.map((lesson) => lesson.localId !== lessonLocalId ? lesson : {
        ...lesson,
        quiz: lesson.quiz ? { ...lesson.quiz, questions: lesson.quiz.questions.map((question) => question.localId !== questionLocalId ? question : {
          ...question,
          choices: question.choices.filter((choice) => choice.localId !== choiceLocalId),
        }) } : null,
      }),
    }));
  }

  async function saveCourse(publish = false) {
    setStatus('saving');
    setMessage('');
    try {
      const payload = {
        title: course.title,
        slug: course.slug || liveCourseSlug,
        subtitle: course.subtitle,
        short_description: course.short_description,
        description: course.description,
        learning_objectives: course.learning_objectives,
        requirements: course.requirements,
        target_audience: course.target_audience,
        tags: course.tags,
        category: course.category || null,
        level: course.level,
        status: publish ? 'published' : course.status,
        language: course.language,
        duration_hours: Number(course.duration_hours || 1),
        price: Number(course.price || 0),
        is_free: course.is_free,
        notes: course.notes,
        notes_enabled: course.notes_enabled,
      };

      let savedCourseId = courseId;
      if (mode === 'new' || !savedCourseId) {
        const { data } = await api.createCourse(payload);
        savedCourseId = data.id;
        setCourseId(savedCourseId);
        setStatus('saved');
      } else {
        await api.updateCourse(savedCourseId, payload);
      }

      if (course.thumbnail) {
        const fd = new FormData();
        fd.append('thumbnail', course.thumbnail);
        await api.apiClient.patch(`/courses/${savedCourseId}/`, fd);
      }

      for (const [moduleIndex, module] of modules.entries()) {
        let sectionId: number | undefined = module.id;
        if (sectionId) {
          await api.updateSection(sectionId, { title: module.title, order: moduleIndex + 1 });
        } else {
          const { data } = await api.createSection({ course: savedCourseId, title: module.title || `Module ${moduleIndex + 1}`, order: moduleIndex + 1 });
          sectionId = data.id;
          module.id = data.id;
        }

        for (const [lessonIndex, lesson] of module.lessons.entries()) {
          let lessonId = lesson.id;
          const lessonPayload: any = {
            section: sectionId,
            title: lesson.title || `Lesson ${lessonIndex + 1}`,
            lesson_type: lesson.lesson_type,
            order: lessonIndex + 1,
            duration_minutes: Number(lesson.duration_minutes || 0),
            content_text: lesson.content_text,
            video_url: lesson.video_url,
            is_preview: lesson.is_preview,
          };
          if (lessonId) {
            await api.updateLesson(lessonId, lessonPayload);
          } else {
            const { data } = await api.createLesson(lessonPayload);
            lessonId = data.id;
            lesson.id = data.id;
          }

          if (lesson.file) {
            const fd = new FormData();
            fd.append('file', lesson.file);
            await api.apiClient.patch(`/lessons/${lessonId}/`, fd);
          }

          if (lesson.quiz) {
            let quizId = lesson.quiz.id;
            const quizPayload = {
              course: savedCourseId,
              section: sectionId,
              lesson: lessonId,
              title: lesson.quiz.title || `${lesson.title} Quiz`,
              passing_score_percent: Number(lesson.quiz.passing_score_percent || 80),
              time_limit_minutes: Number(lesson.quiz.time_limit_minutes || 0),
              max_attempts: Number(lesson.quiz.max_attempts || 3),
              randomize_questions: lesson.quiz.randomize_questions,
              is_final_exam: false,
            };
            if (quizId) {
              await api.updateQuiz(quizId, quizPayload);
            } else {
              const { data } = await api.createQuiz(quizPayload);
              quizId = data.id;
              lesson.quiz.id = data.id;
            }

            for (const [questionIndex, question] of lesson.quiz.questions.entries()) {
              let questionId = question.id;
              const questionPayload = {
                quiz: quizId,
                text: question.text || `Question ${questionIndex + 1}`,
                question_type: question.question_type,
                order: questionIndex + 1,
                points: Number(question.points || 1),
                correct_text_answer: '',
              };
              if (questionId) {
                await api.updateQuestion(questionId, questionPayload);
              } else {
                const { data } = await api.createQuestion(questionPayload);
                questionId = data.id;
                question.id = data.id;
              }

              for (const [choiceIndex, choice] of question.choices.entries()) {
                const choicePayload = {
                  question: questionId,
                  text: choice.text || `Choice ${choiceIndex + 1}`,
                  is_correct: !!choice.is_correct,
                  order: choiceIndex + 1,
                };
                if (choice.id) {
                  await api.updateChoice(choice.id, choicePayload);
                } else {
                  await api.createChoice(choicePayload);
                }
              }
            }
          }
        }
      }

      setStatus('saved');
      setMessage(publish ? 'Course published successfully.' : 'Course saved as draft.');
      if (publish) {
        router.push('/dashboard');
      }
    } catch (err: any) {
      console.error('Failed to save course builder state:', err);
      setStatus('error');
      setMessage(err?.response?.data ? JSON.stringify(err.response.data) : 'Course could not be saved. Please review the form and try again.');
    }
  }

  const totalLessons = modules.reduce((sum, module) => sum + module.lessons.length, 0);
  const totalQuestions = modules.reduce(
    (sum, module) => sum + module.lessons.reduce((lessonSum, lesson) => lessonSum + (lesson.quiz?.questions.length ?? 0), 0),
    0,
  );

  if (isLoading) return <div className="container section">Loading builder…</div>;

  return (
    <div className="container section" style={{ maxWidth: 1400 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
        <div>
          <p style={{ color: 'var(--brand)', fontSize: 12, textTransform: 'uppercase', letterSpacing: 1.2, margin: 0 }}>{mode === 'new' ? 'Create' : 'Edit'} course</p>
          <h1 style={{ margin: '4px 0 0', fontSize: 30 }}>{course.title || 'New Course'}</h1>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button className="btn" type="button" onClick={() => setActivePanel('preview')}>
            <Eye size={14} /> Preview
          </button>
          <button className="btn" type="button" onClick={() => saveCourse(false)} disabled={status === 'saving'}>
            <Save size={14} /> {status === 'saving' ? 'Saving...' : 'Save Draft'}
          </button>
          <button className="btn btn-primary" type="button" onClick={() => saveCourse(true)} disabled={status === 'saving'}>
            <CheckCircle2 size={14} /> Publish
          </button>
        </div>
      </div>

      {status !== 'idle' && message && (
        <div className={`card ${status === 'error' ? 'danger' : ''}`} style={{ marginBottom: 18, borderColor: status === 'error' ? 'var(--danger)' : 'var(--brand)' }}>
          <p style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 8, color: status === 'error' ? 'var(--danger)' : 'var(--brand)' }}>
            {status === 'error' ? <AlertCircle size={15} /> : <CheckCircle2 size={15} />}
            {message}
          </p>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '280px minmax(0, 1fr)', gap: 24 }}>
        <aside className="card" style={{ padding: 16, height: 'fit-content', position: 'sticky', top: 20 }}>
          <p style={{ fontWeight: 700, letterSpacing: '0.08em', fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>COURSE BUILDER</p>
          <nav style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <button type="button" className={activePanel === 'info' ? 'btn btn-primary' : 'btn'} onClick={() => setActivePanel('info')}>Course Information</button>
            <button type="button" className={activePanel === 'structure' ? 'btn btn-primary' : 'btn'} onClick={() => setActivePanel('structure')}>Curriculum</button>
            <button type="button" className={activePanel === 'preview' ? 'btn btn-primary' : 'btn'} onClick={() => setActivePanel('preview')}>Preview</button>
          </nav>

          <div style={{ marginTop: 20, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
            <p style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', margin: '0 0 10px' }}>Quick stats</p>
            <div style={{ display: 'grid', gap: 8 }}>
              <div className="card" style={{ padding: 10 }}>
                <p style={{ margin: 0, fontSize: 12, color: 'var(--text-muted)' }}>Modules</p>
                <p style={{ margin: '4px 0 0', fontWeight: 700, fontSize: 20 }}>{modules.length}</p>
              </div>
              <div className="card" style={{ padding: 10 }}>
                <p style={{ margin: 0, fontSize: 12, color: 'var(--text-muted)' }}>Lessons</p>
                <p style={{ margin: '4px 0 0', fontWeight: 700, fontSize: 20 }}>{totalLessons}</p>
              </div>
              <div className="card" style={{ padding: 10 }}>
                <p style={{ margin: 0, fontSize: 12, color: 'var(--text-muted)' }}>Questions</p>
                <p style={{ margin: '4px 0 0', fontWeight: 700, fontSize: 20 }}>{totalQuestions}</p>
              </div>
            </div>
          </div>
        </aside>

        <main style={{ minWidth: 0 }}>
          {activePanel === 'info' && (
            <div className="card" style={{ padding: 20 }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16 }}>
                <div style={{ gridColumn: '1 / -1' }}>
                  <label className="label">Course title</label>
                  <input className="input" value={course.title} onChange={(e) => updateCourseField('title', e.target.value)} placeholder="Introduction to Startup Business" />
                </div>
                <div>
                  <label className="label">Slug</label>
                  <input className="input" value={course.slug || liveCourseSlug} onChange={(e) => updateCourseField('slug', e.target.value)} />
                </div>
                <div>
                  <label className="label">Course level</label>
                  <select className="input" value={course.level} onChange={(e) => updateCourseField('level', e.target.value)}>
                    <option value="beginner">Beginner</option>
                    <option value="intermediate">Intermediate</option>
                    <option value="advanced">Advanced</option>
                  </select>
                </div>
                <div>
                  <label className="label">Language</label>
                  <input className="input" value={course.language} onChange={(e) => updateCourseField('language', e.target.value)} />
                </div>
                <div>
                  <label className="label">Duration (hours)</label>
                  <input className="input" type="number" value={course.duration_hours} onChange={(e) => updateCourseField('duration_hours', Number(e.target.value || 1))} />
                </div>
                <div>
                  <label className="label">Category</label>
                  <select className="input" value={course.category} onChange={(e) => updateCourseField('category', e.target.value)}>
                    <option value="">Select category</option>
                    {categories.map((category) => (
                      <option key={category.id} value={category.id}>{category.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="label">Status</label>
                  <select className="input" value={course.status} onChange={(e) => updateCourseField('status', e.target.value)}>
                    <option value="draft">Draft</option>
                    <option value="published">Published</option>
                    <option value="pending_approval">Pending approval</option>
                  </select>
                </div>
                <div>
                  <label className="label">Price</label>
                  <input className="input" type="number" value={course.price} onChange={(e) => updateCourseField('price', e.target.value)} disabled={course.is_free} />
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <input type="checkbox" checked={course.is_free} onChange={(e) => updateCourseField('is_free', e.target.checked)} />
                  <label className="label" style={{ margin: 0 }}>Free course</label>
                </div>
              </div>

              <div style={{ marginTop: 18 }}>
                <label className="label">Subtitle</label>
                <input className="input" value={course.subtitle} onChange={(e) => updateCourseField('subtitle', e.target.value)} />
              </div>

              <div style={{ marginTop: 18 }}>
                <label className="label">Short description</label>
                <textarea className="input" value={course.short_description} onChange={(e) => updateCourseField('short_description', e.target.value)} rows={3} />
              </div>

              <div style={{ marginTop: 18 }}>
                <label className="label">Full description</label>
                <RichTextEditor value={course.description} onChange={(html) => updateCourseField('description', html)} placeholder="Write the course overview and learning promise." />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 16, marginTop: 18 }}>
                <div>
                  <label className="label">Learning objectives</label>
                  <textarea className="input" value={course.learning_objectives} onChange={(e) => updateCourseField('learning_objectives', e.target.value)} rows={5} />
                </div>
                <div>
                  <label className="label">Requirements</label>
                  <textarea className="input" value={course.requirements} onChange={(e) => updateCourseField('requirements', e.target.value)} rows={5} />
                </div>
                <div>
                  <label className="label">Target audience</label>
                  <textarea className="input" value={course.target_audience} onChange={(e) => updateCourseField('target_audience', e.target.value)} rows={5} />
                </div>
              </div>

              <div style={{ marginTop: 18 }}>
                <label className="label">Tags</label>
                <input className="input" value={course.tags} onChange={(e) => updateCourseField('tags', e.target.value)} placeholder="startup, ai, business, finance" />
              </div>

              <div style={{ marginTop: 18 }}>
                <label className="label">Course thumbnail</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                  <div style={{ width: 120, height: 82, borderRadius: 10, background: 'var(--surface-2)', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    {thumbnailPreview ? <img src={thumbnailPreview} alt="Course thumbnail" style={{ width: '100%', height: '100%', objectFit: 'cover' }} /> : <Upload size={20} color="var(--text-muted)" />}
                  </div>
                  <label className="btn" style={{ cursor: 'pointer' }}>
                    Upload image
                    <input type="file" accept="image/*" onChange={(e) => {
                      const file = e.target.files?.[0] ?? null;
                      updateCourseField('thumbnail', file);
                      setThumbnailPreview(file ? URL.createObjectURL(file) : null);
                    }} style={{ display: 'none' }} />
                  </label>
                </div>
              </div>

              <div style={{ marginTop: 18 }}>
                <label style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <input type="checkbox" checked={course.notes_enabled} onChange={(e) => updateCourseField('notes_enabled', e.target.checked)} />
                  Show course notes
                </label>
                <div style={{ marginTop: 12 }}>
                  <label className="label">Notes</label>
                  <RichTextEditor value={course.notes} onChange={(html) => updateCourseField('notes', html)} placeholder="Optional notes for learners." />
                </div>
              </div>
            </div>
          )}

          {activePanel === 'structure' && (
            <div className="card" style={{ padding: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, gap: 12, flexWrap: 'wrap' }}>
                <div>
                  <h2 style={{ margin: 0, fontSize: 22 }}>Course structure</h2>
                  <p style={{ margin: '6px 0 0', color: 'var(--text-muted)', fontSize: 13 }}>Build modules, lessons, and lesson quizzes in one place.</p>
                </div>
                <button className="btn btn-primary" type="button" onClick={addModule}><Plus size={14} /> Add module</button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                {modules.map((module, moduleIndex) => (
                  <div key={module.localId} className="card" style={{ padding: 16, background: 'var(--surface-1)' }}>
                    <div style={{ display: 'flex', gap: 10, alignItems: 'center', justifyContent: 'space-between', marginBottom: 12, flexWrap: 'wrap' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0, flex: 1 }}>
                        <GripVertical size={14} color="var(--text-muted)" />
                        <input
                          className="input"
                          value={module.title}
                          onChange={(e) => updateModule(module.localId, { title: e.target.value })}
                          style={{ fontWeight: 700, flex: 1 }}
                          placeholder={`Module ${moduleIndex + 1}`}
                        />
                      </div>
                      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                        <button className="btn" type="button" onClick={() => moveModule('up', module.localId)} title="Move up">↑</button>
                        <button className="btn" type="button" onClick={() => moveModule('down', module.localId)} title="Move down">↓</button>
                        <button className="btn" type="button" onClick={() => duplicateModule(module.localId)}><Copy size={14} /></button>
                        <button className="btn" type="button" onClick={() => deleteModule(module.localId)}><Trash2 size={14} /></button>
                      </div>
                    </div>

                    <textarea className="input" value={module.description} onChange={(e) => updateModule(module.localId, { description: e.target.value })} rows={2} placeholder="Module description" />

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '16px 0 10px' }}>
                      <p style={{ margin: 0, fontWeight: 600 }}>Lessons</p>
                      <button className="btn" type="button" onClick={() => addLesson(module.localId)}><Plus size={14} /> Add lesson</button>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                      {module.lessons.length === 0 && <div className="card" style={{ padding: 14, color: 'var(--text-muted)' }}>No lessons yet. Add one to start building the module.</div>}
                      {module.lessons.map((lesson, lessonIndex) => (
                        <div key={lesson.localId} className="card" style={{ padding: 14, background: 'var(--surface)' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center', marginBottom: 10, flexWrap: 'wrap' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1 }}>
                              <GripVertical size={14} color="var(--text-muted)" />
                              <input
                                className="input"
                                value={lesson.title}
                                onChange={(e) => updateLesson(module.localId, lesson.localId, { title: e.target.value, slug: e.target.value ? slugify(e.target.value) : '' })}
                                placeholder={`Lesson ${lessonIndex + 1}`}
                                style={{ fontWeight: 600, flex: 1 }}
                              />
                            </div>
                            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                              <button className="btn" type="button" onClick={() => moveLesson(module.localId, lesson.localId, 'up')}>↑</button>
                              <button className="btn" type="button" onClick={() => moveLesson(module.localId, lesson.localId, 'down')}>↓</button>
                              <button className="btn" type="button" onClick={() => duplicateLesson(module.localId, lesson.localId)}><Copy size={13} /></button>
                              <button className="btn" type="button" onClick={() => deleteLesson(module.localId, lesson.localId)}><Trash2 size={13} /></button>
                            </div>
                          </div>

                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
                            <div>
                              <label className="label">Lesson type</label>
                              <select className="input" value={lesson.lesson_type} onChange={(e) => updateLesson(module.localId, lesson.localId, { lesson_type: e.target.value as LessonDraft['lesson_type'] })}>
                                <option value="text">Text</option>
                                <option value="video">Video</option>
                                <option value="pdf">PDF</option>
                                <option value="powerpoint">PowerPoint</option>
                                <option value="audio">Audio</option>
                              </select>
                            </div>
                            <div>
                              <label className="label">Estimated duration</label>
                              <input className="input" type="number" value={lesson.duration_minutes} onChange={(e) => updateLesson(module.localId, lesson.localId, { duration_minutes: Number(e.target.value || 0) })} />
                            </div>
                            <div>
                              <label className="label">Slug</label>
                              <input className="input" value={lesson.slug || slugify(lesson.title)} onChange={(e) => updateLesson(module.localId, lesson.localId, { slug: e.target.value })} />
                            </div>
                          </div>

                          <div style={{ marginTop: 12 }}>
                            <label className="label">Lesson description</label>
                            <textarea className="input" rows={2} value={lesson.description} onChange={(e) => updateLesson(module.localId, lesson.localId, { description: e.target.value })} />
                          </div>

                          <div style={{ marginTop: 12 }}>
                            <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <input type="checkbox" checked={lesson.is_preview} onChange={(e) => updateLesson(module.localId, lesson.localId, { is_preview: e.target.checked })} />
                              Free preview lesson
                            </label>
                          </div>

                          {lesson.lesson_type === 'video' && (
                            <div style={{ marginTop: 12 }}>
                              <label className="label">Video URL</label>
                              <input className="input" value={lesson.video_url} onChange={(e) => updateLesson(module.localId, lesson.localId, { video_url: e.target.value })} placeholder="https://youtube.com/..." />
                            </div>
                          )}

                          <div style={{ marginTop: 12 }}>
                            <label className="label">Lesson content</label>
                            <RichTextEditor value={lesson.content_text} onChange={(html) => updateLesson(module.localId, lesson.localId, { content_text: html })} placeholder="Write rich lesson content here." />
                          </div>

                          <div style={{ marginTop: 12 }}>
                            <label className="label">Learning materials</label>
                            <div className="card" style={{ padding: 12, color: 'var(--text-muted)' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                                <button className="btn" type="button"><Upload size={14} /> Add PDF</button>
                                <button className="btn" type="button"><FileText size={14} /> Add document</button>
                                <button className="btn" type="button"><BookOpen size={14} /> Add resource</button>
                              </div>
                              <p style={{ margin: '8px 0 0', fontSize: 12 }}>Material support is included in the course builder flow. Upload and manage PDF, slides, docs, videos, and resource links from this lesson card.</p>
                            </div>
                          </div>

                          <div style={{ marginTop: 16 }}>
                            {!lesson.quiz ? (
                              <button className="btn btn-primary" type="button" onClick={() => ensureQuiz(module.localId, lesson.localId)}><Plus size={14} /> Add quiz</button>
                            ) : (
                              <div style={{ border: '1px solid var(--border)', borderRadius: 10, padding: 14, background: 'rgba(255,255,255,0.02)' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12, marginBottom: 12 }}>
                                  <div>
                                    <p style={{ margin: 0, fontWeight: 700 }}>Lesson quiz</p>
                                    <p style={{ margin: '4px 0 0', color: 'var(--text-muted)', fontSize: 12 }}>{lesson.quiz.questions.length} questions • pass at {lesson.quiz.passing_score_percent}%</p>
                                  </div>
                                  <button className="btn" type="button" onClick={() => removeQuiz(module.localId, lesson.localId)}><Trash2 size={13} /> Remove quiz</button>
                                </div>

                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 12, marginBottom: 12 }}>
                                  <div>
                                    <label className="label">Quiz title</label>
                                    <input className="input" value={lesson.quiz.title} onChange={(e) => updateLesson(module.localId, lesson.localId, { quiz: { ...lesson.quiz!, title: e.target.value } })} />
                                  </div>
                                  <div>
                                    <label className="label">Passing score</label>
                                    <input className="input" type="number" value={lesson.quiz.passing_score_percent} onChange={(e) => updateLesson(module.localId, lesson.localId, { quiz: { ...lesson.quiz!, passing_score_percent: Number(e.target.value || 0) } })} />
                                  </div>
                                  <div>
                                    <label className="label">Attempts</label>
                                    <input className="input" type="number" value={lesson.quiz.max_attempts} onChange={(e) => updateLesson(module.localId, lesson.localId, { quiz: { ...lesson.quiz!, max_attempts: Number(e.target.value || 0) } })} />
                                  </div>
                                </div>

                                <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                                  {lesson.quiz.questions.map((question, questionIndex) => (
                                    <div key={question.localId} className="card" style={{ padding: 12 }}>
                                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                                        <p style={{ margin: 0, fontWeight: 700 }}>Question {questionIndex + 1}</p>
                                        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                                          <button className="btn" type="button" onClick={() => moveQuestion(module.localId, lesson.localId, question.localId, 'up')}>↑</button>
                                          <button className="btn" type="button" onClick={() => moveQuestion(module.localId, lesson.localId, question.localId, 'down')}>↓</button>
                                          <button className="btn" type="button" onClick={() => duplicateQuestion(module.localId, lesson.localId, question.localId)}><Copy size={12} /></button>
                                          <button className="btn" type="button" onClick={() => deleteQuestion(module.localId, lesson.localId, question.localId)}><Trash2 size={12} /></button>
                                        </div>
                                      </div>

                                      <div style={{ marginTop: 10, display: 'grid', gap: 10 }}>
                                        <div>
                                          <label className="label">Question text</label>
                                          <textarea className="input" rows={2} value={question.text} onChange={(e) => updateQuestion(module.localId, lesson.localId, question.localId, { text: e.target.value })} />
                                        </div>
                                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 10 }}>
                                          <div>
                                            <label className="label">Question type</label>
                                            <select className="input" value={question.question_type} onChange={(e) => updateQuestion(module.localId, lesson.localId, question.localId, { question_type: e.target.value as QuestionType })}>
                                              {QUESTION_TYPES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                                            </select>
                                          </div>
                                          <div>
                                            <label className="label">Points</label>
                                            <input className="input" type="number" value={question.points} onChange={(e) => updateQuestion(module.localId, lesson.localId, question.localId, { points: Number(e.target.value || 1) })} />
                                          </div>
                                        </div>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                          <input type="checkbox" checked={question.required} onChange={(e) => updateQuestion(module.localId, lesson.localId, question.localId, { required: e.target.checked })} />
                                          <label>Required</label>
                                        </div>
                                      </div>

                                      <div style={{ marginTop: 12 }}>
                                        <label className="label">Choices</label>
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                                          {question.choices.map((choice, choiceIndex) => (
                                            <div key={choice.localId} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                                              <input
                                                type={question.question_type === 'checkbox' ? 'checkbox' : 'radio'}
                                                name={`choice-${question.localId}`}
                                                checked={choice.is_correct}
                                                onChange={() => updateChoice(module.localId, lesson.localId, question.localId, choice.localId, { is_correct: true })}
                                              />
                                              <input
                                                className="input"
                                                value={choice.text}
                                                onChange={(e) => updateChoice(module.localId, lesson.localId, question.localId, choice.localId, { text: e.target.value })}
                                                placeholder={`Choice ${choiceIndex + 1}`}
                                              />
                                              <button className="btn" type="button" onClick={() => deleteChoice(module.localId, lesson.localId, question.localId, choice.localId)}><Trash2 size={12} /></button>
                                            </div>
                                          ))}
                                          <button className="btn" type="button" onClick={() => addChoice(module.localId, lesson.localId, question.localId)}><Plus size={12} /> Add choice</button>
                                        </div>
                                      </div>

                                      <div style={{ marginTop: 12 }}>
                                        <label className="label">Explanation</label>
                                        <textarea className="input" rows={2} value={question.explanation} onChange={(e) => updateQuestion(module.localId, lesson.localId, question.localId, { explanation: e.target.value })} />
                                      </div>
                                    </div>
                                  ))}
                                  <button className="btn btn-primary" type="button" onClick={() => addQuestion(module.localId, lesson.localId)}><Plus size={14} /> Add question</button>
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activePanel === 'preview' && (
            <div className="card" style={{ padding: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                <div>
                  <p style={{ margin: 0, letterSpacing: '0.08em', color: 'var(--text-muted)', fontSize: 11 }}>PREVIEW</p>
                  <h2 style={{ margin: '8px 0 0', fontSize: 28 }}>{course.title || 'Course title'}</h2>
                </div>
                <span className="badge">{course.status}</span>
              </div>

              <div style={{ marginTop: 18, color: 'var(--text-muted)' }} dangerouslySetInnerHTML={{ __html: course.description || '<p>Course description preview appears here.</p>' }} />

              <div style={{ display: 'grid', gap: 12, marginTop: 20 }}>
                {modules.map((module, index) => (
                  <div key={module.localId} className="card" style={{ padding: 16 }}>
                    <p style={{ margin: 0, fontWeight: 700 }}>{index + 1}. {module.title || 'Module title'}</p>
                    <div style={{ marginTop: 10, display: 'grid', gap: 10 }}>
                      {module.lessons.map((lesson, lessonIndex) => (
                        <div key={lesson.localId} style={{ padding: 12, border: '1px solid var(--border)', borderRadius: 8 }}>
                          <p style={{ margin: 0, fontWeight: 600 }}>{lessonIndex + 1}. {lesson.title || 'Lesson title'}</p>
                          <p style={{ margin: '8px 0 0', color: 'var(--text-muted)' }}>{lesson.description || 'Lesson description preview.'}</p>
                          {lesson.quiz && (
                            <div style={{ marginTop: 10 }}>
                              <p style={{ margin: 0, fontWeight: 600 }}>{lesson.quiz.title}</p>
                              <p style={{ margin: '4px 0 0', color: 'var(--text-muted)', fontSize: 12 }}>{lesson.quiz.questions.length} questions • {lesson.quiz.passing_score_percent}% passing score</p>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
