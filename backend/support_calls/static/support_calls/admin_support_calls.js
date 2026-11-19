(function () {
  'use strict';

  const config = document.getElementById('support-call-admin-config');
  if (!config || !window.fetch) return;

  const apiRoot = '/api/support-calls';
  const announced = new Set();
  let pendingCalls = [];
  let audioContext = null;
  let ringTimer = null;
  let alertsEnabled = false;

  const style = document.createElement('style');
  style.textContent = [
    '.ess-call-alerts{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:0 0 16px;padding:12px 16px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;color:#1e3a8a}',
    '.ess-call-alerts button{border:0;border-radius:6px;padding:9px 13px;font-weight:700;cursor:pointer}',
    '.ess-call-enable{background:#1d4ed8;color:#fff}.ess-call-muted{color:#475569}'
  ].join('');
  document.head.appendChild(style);

  const banner = document.createElement('div');
  banner.className = 'ess-call-alerts';
  banner.innerHTML = '<strong>Support call alerts</strong><span class="ess-call-muted">Keep this admin page open to receive incoming-call alerts.</span><button type="button" class="ess-call-enable"></button>';
  const content = document.getElementById('content') || document.body;
  content.insertBefore(banner, content.firstChild);
  const enableButton = banner.querySelector('button');

  function updateEnableButton() {
    enableButton.textContent = alertsEnabled ? 'Desktop alerts & sound enabled' : 'Enable desktop alerts & sound';
    enableButton.disabled = alertsEnabled;
  }

  function startRing() {
    if (!alertsEnabled || !audioContext || ringTimer) return;
    const ring = function () {
      if (!pendingCalls.length || !audioContext) return;
      const oscillator = audioContext.createOscillator();
      const gain = audioContext.createGain();
      oscillator.type = 'sine';
      oscillator.frequency.value = 880;
      gain.gain.setValueAtTime(0.001, audioContext.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.12, audioContext.currentTime + 0.04);
      gain.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + 0.65);
      oscillator.connect(gain);
      gain.connect(audioContext.destination);
      oscillator.start();
      oscillator.stop(audioContext.currentTime + 0.7);
    };
    ring();
    ringTimer = window.setInterval(ring, 2200);
  }

  function stopRing() {
    if (!ringTimer) return;
    window.clearInterval(ringTimer);
    ringTimer = null;
  }

  function notifyCall(call) {
    if (
      announced.has(call.call_id)
      || !alertsEnabled
      || !('Notification' in window)
      || Notification.permission !== 'granted'
    ) return;

    announced.add(call.call_id);
    const notification = new Notification('Incoming ' + (call.mode_label || call.mode) + ' call', {
      body: call.display_name + (call.question ? ': ' + call.question : ''),
      tag: 'ess-support-call-' + call.call_id,
      requireInteraction: false
    });
    notification.onclick = function () {
      window.focus();
      notification.close();
    };
  }

  async function poll() {
    try {
      const response = await fetch(apiRoot + '/admin/', {
        credentials: 'same-origin',
        cache: 'no-store',
        headers: { 'Accept': 'application/json' }
      });
      if (!response.ok) throw new Error(response.status === 403
        ? 'This Django account is not authorized to manage support calls.'
        : 'Could not check the support-call queue.');
      const calls = await response.json();
      pendingCalls = calls.filter(function (call) { return call.status === 'pending'; });
      pendingCalls.forEach(notifyCall);
      if (!pendingCalls.length) {
        stopRing();
      } else {
        startRing();
      }
    } catch (error) {
      banner.querySelector('.ess-call-muted').textContent = error.message
        + ' Sign in with an ESS administrator account and reload this page.';
    }
  }

  enableButton.addEventListener('click', async function () {
    if ('Notification' in window && Notification.permission === 'default') {
      await Notification.requestPermission();
    }
    try {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (AudioContextClass) {
        audioContext = new AudioContextClass();
        await audioContext.resume();
      }
      alertsEnabled = true;
      banner.querySelector('.ess-call-muted').textContent =
        'This page will show incoming calls. Keep it open; desktop notifications depend on browser permission.';
      updateEnableButton();
      pendingCalls.forEach(notifyCall);
      startRing();
    } catch (error) {
      banner.querySelector('.ess-call-muted').textContent = 'Sound could not be enabled: ' + error.message;
    }
  });

  updateEnableButton();
  void poll();
  window.setInterval(poll, 5000);
})();
