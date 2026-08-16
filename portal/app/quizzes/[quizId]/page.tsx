'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getCourse, getQuiz, submitQuiz } from '@/lib/api';

export default function QuizPage() {
  const { quizId } = useParams<{ quizId: string }>();
  const router = useRouter();
  const [quiz, setQuiz] = useState<any>(null);
  const [course, setCourse] = useState<any>(null);
  const [responses, setResponses] = useState<Record<number, { choiceIds: number[]; text: string }>>({});
  const [result, setResult] = useState<any>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      const res = await getQuiz(Number(quizId));
      const quizData = res.data;
      setQuiz(quizData);

      if (quizData?.course) {
        try {
          const courseRes = await getCourse(quizData.course);
          setCourse(courseRes.data);
        } catch (err) {
          console.warn('Failed to load course for quiz navigation:', err);
        }
      }
    }

    void load();
  }, [quizId]);

  function toggle(qid: number, cid: number, multi: boolean) {
    setResponses((prev) => {
      const current = prev[qid]?.choiceIds ?? [];
      const updated = multi
        ? current.includes(cid) ? current.filter((x) => x !== cid) : [...current, cid]
        : [cid];
      return { ...prev, [qid]: { choiceIds: updated, text: prev[qid]?.text ?? '' } };
    });
  }

  function setText(qid: number, text: string) {
    setResponses((prev) => ({ ...prev, [qid]: { choiceIds: prev[qid]?.choiceIds ?? [], text } }));
  }

  function handleSuccessfulResult() {
    if (!quiz) return;

    if (quiz.is_final_exam) {
      const slug = course?.slug;
      if (slug) router.push(`/courses/${slug}`);
      else router.push('/profile');
      return;
    }

    if (quiz.lesson && course?.sections) {
      const allLessons = course.sections.flatMap((section: any) => section.lessons ?? []);
      const currentIndex = allLessons.findIndex((lesson: any) => lesson.id === quiz.lesson);
      const nextLesson = allLessons[currentIndex + 1] ?? null;
      if (nextLesson?.id) {
        router.push(`/courses/${course.slug}/lessons/${nextLesson.id}`);
        return;
      }
    }

    if (course?.slug) router.push(`/courses/${course.slug}`);
    else router.push('/dashboard');
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      const answers = quiz.questions.map((q: any) => ({
        question_id: q.id,
        selected_choice_ids: responses[q.id]?.choiceIds ?? [],
        text_answer: responses[q.id]?.text ?? '',
      }));
      const { data } = await submitQuiz(Number(quizId), answers);
      setResult(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Could not submit — try again.');
    } finally {
      setSubmitting(false);
    }
  }

  if (!quiz) return <div className="container section">Loading...</div>;

  if (result) {
    return (
      <div className="container section" style={{ maxWidth: 480, textAlign: 'center' }}>
        <p style={{ fontSize: 52, fontWeight: 800, color: result.passed ? 'var(--brand)' : 'var(--danger)', margin: 0 }}>
          {result.score_percent}%
        </p>
        <p style={{ fontSize: 18, margin: '10px 0 24px' }}>
          {result.passed
            ? quiz.is_final_exam
              ? '🎉 You passed the final exam and your certificate is ready in your profile.'
              : '🎉 You passed! The next lesson is now unlocked.'
            : `You need ${quiz.passing_score_percent}% to pass — try again.`}
        </p>
        {result.passed ? (
          <button className="btn btn-primary" onClick={handleSuccessfulResult}>Continue</button>
        ) : (
          <button className="btn btn-primary" onClick={() => { setResult(null); setResponses({}); }}>Retry Quiz</button>
        )}
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="container section" style={{ maxWidth: 640 }}>
      <h1 style={{ fontSize: 22, marginBottom: 4 }}>{quiz.title}</h1>
      <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 24 }}>
        {quiz.questions.length} questions · each worth {(100 / quiz.questions.length).toFixed(0)}% · pass at {quiz.passing_score_percent}%
      </p>

      {error && <p style={{ color: 'var(--danger)', marginBottom: 16 }}>{error}</p>}

      {quiz.questions.map((q: any, idx: number) => (
        <div key={q.id} className="card" style={{ marginBottom: 14 }}>
          <p style={{ fontWeight: 600, marginBottom: 10 }}>{idx + 1}. {q.text}</p>

          {['multiple_choice', 'true_false'].includes(q.question_type) && q.choices.map((c: any) => (
            <label key={c.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 0', fontSize: 14, cursor: 'pointer' }}>
              <input type="radio" name={`q${q.id}`} checked={!!responses[q.id]?.choiceIds.includes(c.id)} onChange={() => toggle(q.id, c.id, false)} />
              {c.text}
            </label>
          ))}

          {q.question_type === 'checkbox' && q.choices.map((c: any) => (
            <label key={c.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 0', fontSize: 14, cursor: 'pointer' }}>
              <input type="checkbox" checked={!!responses[q.id]?.choiceIds.includes(c.id)} onChange={() => toggle(q.id, c.id, true)} />
              {c.text}
            </label>
          ))}

          {['fill_blank', 'essay'].includes(q.question_type) && (
            q.question_type === 'essay' ? (
              <textarea className="input" rows={4} value={responses[q.id]?.text ?? ''} onChange={(e) => setText(q.id, e.target.value)} />
            ) : (
              <input className="input" value={responses[q.id]?.text ?? ''} onChange={(e) => setText(q.id, e.target.value)} />
            )
          )}
        </div>
      ))}

      <button className="btn btn-primary" type="submit" disabled={submitting} style={{ width: '100%' }}>
        {submitting ? 'Submitting...' : 'Submit Quiz'}
      </button>
    </form>
  );
}
