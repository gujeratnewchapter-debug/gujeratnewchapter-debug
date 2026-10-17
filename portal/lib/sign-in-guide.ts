export type SignInStep = {
  title: string;
  desc: string;
};

const ACCOUNT_SETUP_FALLBACKS: SignInStep[] = [
  { title: 'Create your account', desc: 'Choose Sign up and enter the details requested on the registration form.' },
  { title: 'Use your preferred sign-up method', desc: 'Register with email, or continue with a supported Google or GitHub account.' },
  { title: 'Check your inbox', desc: 'If you registered with email, look for the verification message we send you.' },
  { title: 'Verify your email', desc: 'Open the verification link before signing in with your email and password.' },
  { title: 'Return to sign in', desc: 'After verification, use the same email and password you registered with.' },
  { title: 'Complete your profile', desc: 'Add the details that help make your learning experience your own.' },
  { title: 'Choose a learning goal', desc: 'Decide what you would like to learn or build first.' },
];

const LEARNING_FALLBACKS: SignInStep[] = [
  { title: 'Browse the course catalog', desc: 'Explore practical topics in entrepreneurship, AI, finance, marketing, and leadership.' },
  { title: 'Choose a course', desc: 'Select a learning path that matches your interests and goals.' },
  { title: 'Enroll and open the first lesson', desc: 'Join the course and begin learning at your own pace.' },
  { title: 'Learn with your AI Tutor', desc: 'Ask questions and get help when a lesson concept is unclear.' },
  { title: 'Practice as you go', desc: 'Work through activities and quizzes to check your understanding.' },
  { title: 'Complete your course', desc: 'Finish the required lessons and quizzes to earn your certificate.' },
];

function normalizeSteps(value: unknown): SignInStep[] {
  if (!Array.isArray(value)) return [];

  return value.map((item) => {
    if (Array.isArray(item)) {
      return { title: String(item[0] ?? ''), desc: String(item[1] ?? '') };
    }

    if (item && typeof item === 'object') {
      const step = item as Record<string, unknown>;
      return {
        title: String(step.title ?? ''),
        desc: String(step.desc ?? step.description ?? ''),
      };
    }

    return { title: '', desc: '' };
  });
}

function fillSteps(configured: SignInStep[], fallbacks: SignInStep[]): SignInStep[] {
  return fallbacks.map((fallback, index) => {
    const configuredStep = configured[index];
    return configuredStep?.title || configuredStep?.desc
      ? {
        title: configuredStep.title || fallback.title,
        desc: configuredStep.desc || fallback.desc,
      }
      : fallback;
  });
}

export function getSignInProcessSteps(content: unknown, lang = 'en') {
  const rawContent = content && typeof content === 'object'
    ? content as Record<string, unknown>
    : {};
  const localizedContent = rawContent[lang] && typeof rawContent[lang] === 'object'
    ? rawContent[lang] as Record<string, unknown>
    : rawContent;

  const accountSetup = normalizeSteps(localizedContent.account_setup_steps);
  const learning = normalizeSteps(localizedContent.learning_steps);
  const accountSetupTitle = typeof localizedContent.account_setup_title === 'string'
    ? localizedContent.account_setup_title.trim()
    : '';
  const learningTitle = typeof localizedContent.learning_title === 'string'
    ? localizedContent.learning_title.trim()
    : '';
  if (accountSetup.length || learning.length) {
    return {
      accountSetupTitle: accountSetupTitle || 'Set up your account',
      learningTitle: learningTitle || 'Start learning',
      accountSetupSteps: fillSteps(accountSetup, ACCOUNT_SETUP_FALLBACKS),
      learningSteps: fillSteps(learning, LEARNING_FALLBACKS),
    };
  }

  const legacyItems = normalizeSteps(localizedContent.items ?? rawContent.items);
  return {
    accountSetupTitle: accountSetupTitle || 'Set up your account',
    learningTitle: learningTitle || 'Start learning',
    accountSetupSteps: fillSteps(legacyItems.slice(0, 2), ACCOUNT_SETUP_FALLBACKS),
    learningSteps: fillSteps(
      legacyItems.slice(2, 2 + LEARNING_FALLBACKS.length),
      LEARNING_FALLBACKS,
    ),
  };
}
