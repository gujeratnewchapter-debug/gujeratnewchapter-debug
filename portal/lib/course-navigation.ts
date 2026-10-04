type CourseLesson = { id: number };
type CourseSection = { id: number; lessons?: CourseLesson[] };

export function getNextLessonPath(
  sections: CourseSection[] | undefined,
  courseSlug: string,
  currentLessonId: number | undefined,
) {
  if (!sections || !currentLessonId || !courseSlug) return null;
  const lessons = sections.flatMap((section) => section.lessons ?? []);
  const currentIndex = lessons.findIndex((lesson) => Number(lesson.id) === Number(currentLessonId));
  const nextLesson = currentIndex >= 0 ? lessons[currentIndex + 1] : null;

  return nextLesson
    ? `/courses/${encodeURIComponent(courseSlug)}/lessons/${nextLesson.id}`
    : null;
}

export function getSectionContinuePath(
  sections: CourseSection[] | undefined,
  courseSlug: string,
  sectionId: number,
) {
  const section = sections?.find((item) => Number(item.id) === Number(sectionId));
  const lastLessonId = section?.lessons?.at(-1)?.id;
  return getNextLessonPath(sections, courseSlug, lastLessonId) ?? '/profile#certificates';
}

export function getResumeLessonPath(
  sections: CourseSection[] | undefined,
  courseSlug: string,
  completedLessonIds: number[],
) {
  if (!sections || !courseSlug) return null;

  const completed = new Set(completedLessonIds.map(Number));
  const nextLesson = sections
    .flatMap((section) => section.lessons ?? [])
    .find((lesson) => lesson.id != null && !completed.has(Number(lesson.id)));

  return nextLesson
    ? `/courses/${encodeURIComponent(courseSlug)}/lessons/${nextLesson.id}`
    : null;
}
