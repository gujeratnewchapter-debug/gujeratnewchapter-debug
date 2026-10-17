export function splitSignInProcess<T>(steps: T[]) {
  return {
    accountSetupSteps: steps.slice(0, 2),
    learningSteps: steps.slice(2),
  };
}
