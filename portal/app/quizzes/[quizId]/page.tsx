'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getCourse, getQuiz, submitQuiz } from '@/lib/api';
import { InnovationLoader } from '@/components/InnovationLoader';
import { getNextLessonPath, getSectionContinuePath } from '@/lib/course-navigation';

export default function QuizPage() {
  const { quizId } = useParams<{ quizId: string }>();
  const router = useRouter();
  const [quiz, setQuiz] = useState<any>(null);
  const [course, setCourse] = useState<any>(null);
  const [loadingQuiz, setLoadingQuiz] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [responses, setResponses] = useState<Record<number, { choiceIds: number[]; text: string }>>({});
  const [result, setResult] = useState<any>(null);
  const [submitting, setSubmitting] = useState(false);
  const [continuing, setContinuing] = useState(false);
  const [error, setError] = useState('');
  const [startedAt] = useState(() => Date.now());

  const loadQuiz = React.useCallback(async () => {
    setLoadingQuiz(true);
    setLoadError('');
    try {
      const res = await getQuiz(Number(quizId));
      const quizData = res.data;
      setQuiz(quizData);

      if (quizData?.course) {
        try {
          const courseRes = await getCourse(quizData.course);
          setCourse(courseRes.data);
        } catch (err) {
          console.warn('Failed to load course for quiz navigation:', err);
          setCourse(null);
        }
      }
    } catch (err) {
      console.error('Failed to load quiz:', quizId, err);
      setQuiz(null);
      setLoadError('This quiz could not be loaded. Retry; your course progress is saved.');
    } finally {
      setLoadingQuiz(false);
    }
  }, [quizId]);

  useEffect(() => {
    void loadQuiz();
  }, [loadQuiz]);

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

  async function handleSuccessfulResult() {
    if (!quiz) return;
    setContinuing(true);
    setError('');

    try {
      if (quiz.is_final_exam && !quiz.section) {
        router.push('/profile#certificates');
        return;
      }

      let currentCourse = course;
      if ((quiz.lesson || quiz.section) && quiz.course) {
        const { data } = await getCourse(quiz.course, true);
        currentCourse = data;
        setCourse(data);
      }

      if (quiz.lesson && currentCourse?.sections && currentCourse.slug) {
        const nextLessonPath = getNextLessonPath(
          currentCourse.sections,
          currentCourse.slug,
          Number(quiz.lesson),
        );
        router.push(nextLessonPath ?? '/profile#certificates');
        return;
      }

      if (quiz.section && currentCourse?.sections && currentCourse.slug) {
        router.push(getSectionContinuePath(
          currentCourse.sections,
          currentCourse.slug,
          Number(quiz.section),
        ));
        return;
      }

      if (quiz.is_final_exam) {
        router.push('/profile#certificates');
        return;
      }

      setError('You passed. We could not load the next lesson. Please try Continue again.');
    } catch (err) {
      console.error('Failed to load the next lesson after passing the quiz:', err);
      setError('You passed, but the next lesson could not be loaded. Please try Continue again.');
    } finally {
      setContinuing(false);
    }

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
      const { data } = await submitQuiz(Number(quizId), answers, Math.round((Date.now() - startedAt) / 1000));
      setResult(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Could not submit — try again.');
    } finally {
      setSubmitting(false);
    }
  }

  if (loadingQuiz) return <div className="container section"><InnovationLoader label="Loading quiz" /></div>;

  if (loadError || !quiz) {
    return (
      <div className="container section" style={{ maxWidth: 560, textAlign: 'center' }}>
        <div className="card" role="alert" style={{ padding: 24 }}>
          <h1 style={{ fontSize: 22, marginTop: 0 }}>Quiz temporarily unavailable</h1>
          <p style={{ color: 'var(--text-muted)' }}>{loadError || 'This quiz is unavailable right now.'}</p>
          <button className="btn btn-primary" onClick={() => void loadQuiz()} disabled={loadingQuiz}>
            {loadingQuiz ? 'Retrying quiz...' : 'Retry quiz'}
          </button>
        </div>
      </div>
    );
  }

  if (result) {
    return (
      <div className="container section" style={{ maxWidth: 480, textAlign: 'center' }}>
        <p style={{ fontSize: 52, fontWeight: 800, color: result.passed ? 'var(--brand)' : 'var(--danger)', margin: 0 }}>
          {result.score_percent}%
        </p>
        <p style={{ fontSize: 18, margin: '10px 0 24px' }}>
          {result.passed
            ? quiz.is_final_exam
              ? quiz.section
                ? '🎉 You passed the module exam. Continue to the next lesson.'
                : '🎉 You passed the final exam and your certificate is ready in your profile.'
              : '🎉 You passed! The next lesson is now unlocked.'
            : `You need ${quiz.passing_score_percent}% to pass — try again.`}
        </p>
        {result.passed ? (
          <>
            {error && <p role="alert" style={{ color: 'var(--danger)', marginBottom: 16 }}>{error}</p>}
            <button className="btn btn-primary" onClick={handleSuccessfulResult} disabled={continuing}>
              {continuing ? 'Loading next lesson...' : 'Continue'}
            </button>
          </>
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
