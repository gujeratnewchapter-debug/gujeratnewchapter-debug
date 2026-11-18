let supportCallAudioContext: AudioContext | null = null;

export async function enableSupportCallAudio() {
  if (typeof window === 'undefined' || !('AudioContext' in window)) return false;
  supportCallAudioContext ??= new window.AudioContext();
  await supportCallAudioContext.resume();
  return supportCallAudioContext.state === 'running';
}

function playRingbackBurst(context: AudioContext) {
  const startAt = context.currentTime;
  const oscillator = context.createOscillator();
  const gain = context.createGain();
  oscillator.type = 'sine';
  oscillator.frequency.value = 440;
  gain.gain.setValueAtTime(0.0001, startAt);
  gain.gain.exponentialRampToValueAtTime(0.12, startAt + 0.06);
  gain.gain.setValueAtTime(0.12, startAt + 0.82);
  gain.gain.exponentialRampToValueAtTime(0.0001, startAt + 0.9);
  oscillator.connect(gain);
  gain.connect(context.destination);
  oscillator.start(startAt);
  oscillator.stop(startAt + 0.92);
}

export function startSupportCallRingback() {
  if (!supportCallAudioContext || supportCallAudioContext.state !== 'running') return null;

  playRingbackBurst(supportCallAudioContext);
  const interval = window.setInterval(() => {
    if (supportCallAudioContext?.state === 'running') {
      playRingbackBurst(supportCallAudioContext);
    }
  }, 3000);

  return () => window.clearInterval(interval);
}
