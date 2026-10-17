import test from 'node:test';
import assert from 'node:assert/strict';
import { splitSignInProcess } from './sign-in-guide.ts';

test('groups account creation and email verification separately from learning steps', () => {
  const steps = [
    { title: 'Create your account' },
    { title: 'Verify your email' },
    { title: 'Sign in and start learning' },
  ];

  const sections = splitSignInProcess(steps);

  assert.deepEqual(sections.accountSetupSteps, steps.slice(0, 2));
  assert.deepEqual(sections.learningSteps, steps.slice(2));
  assert.deepEqual([...sections.accountSetupSteps, ...sections.learningSteps], steps);
});

test('retains additional CMS-configured learning steps', () => {
  const steps = ['Create account', 'Verify email', 'Sign in', 'Choose a course'];

  assert.deepEqual(splitSignInProcess(steps), {
    accountSetupSteps: ['Create account', 'Verify email'],
    learningSteps: ['Sign in', 'Choose a course'],
  });
});
