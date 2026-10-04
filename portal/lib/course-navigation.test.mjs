import test from 'node:test';
import assert from 'node:assert/strict';
import { getNextLessonPath, getResumeLessonPath, getSectionContinuePath } from './course-navigation.ts';

const courseSections = [
  { id: 10, lessons: [{ id: 101 }, { id: 102 }] },
  { id: 20, lessons: [{ id: 201 }, { id: 202 }] },
];

test('passing a lesson routes to the next lesson, including the next section', () => {
  assert.equal(getNextLessonPath(courseSections, 'startup-course', 102), '/courses/startup-course/lessons/201');
});

test('resume starts from the first unfinished lesson after interruption', () => {
  assert.equal(
    getResumeLessonPath(courseSections, 'startup-course', [101, 102, 201]),
    '/courses/startup-course/lessons/202',
  );
});

test('resume starts the course when no lesson has been completed', () => {
  assert.equal(getResumeLessonPath(courseSections, 'startup-course', []), '/courses/startup-course/lessons/101');
});

test('module final continue targets the next section first lesson', () => {
  assert.equal(getSectionContinuePath(courseSections, 'startup-course', 10), '/courses/startup-course/lessons/201');
});

test('finished course has no resume lesson and module final continue goes to certificates', () => {
  assert.equal(getResumeLessonPath(courseSections, 'startup-course', [101, 102, 201, 202]), null);
  assert.equal(getSectionContinuePath(courseSections, 'startup-course', 20), '/profile#certificates');
});
