(function () {
  'use strict';

  const config = document.getElementById('support-call-admin-config');
  if (!config || !window.fetch) return;

  const apiRoot = '/api/support-calls';
  const frontendUrl = config.dataset.frontendUrl || '';
  const announced = new Set();
  const dismissed = new Set();
  let pendingCalls = [];
  let audioContext = null;
  let ringTimer = null;
  let busy = false;
  let alertsEnabled = false;

  const style = document.createElement('style');
  style.textContent = [
    '.ess-call-alerts{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:0 0 16px;padding:12px 16px;background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;color:#1e3a8a}',
    '.ess-call-alerts button,.ess-call-dialog button{border:0;border-radius:6px;padding:9px 13px;font-weight:700;cursor:pointer}',
    '.ess-call-enable{background:#1d4ed8;color:#fff}.ess-call-muted{color:#475569}',
    '.ess-call-backdrop{position:fixed;inset:0;z-index:10000;display:grid;place-items:center;padding:20px;background:#0f172a99}',
    '.ess-call-dialog{width:min(520px,100%);padding:24px;background:#fff;border-radius:14px;box-shadow:0 24px 70px #0f172a55;color:#0f172a}',
    '.ess-call-dialog h2{margin:0 0 8px;font-size:22px}.ess-call-dialog p{margin:8px 0;color:#475569;line-height:1.5}',
    '.ess-call-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:20px}.ess-call-answer{background:#15803d;color:#fff}.ess-call-reject{background:#b91c1c;color:#fff}.ess-call-dismiss{background:#e2e8f0;color:#0f172a}',
    '.ess-call-error{color:#b91c1c!important;font-weight:600}'
  ].join('');
  document.head.appendChild(style);

  const banner = document.createElement('div');
  banner.className = 'ess-call-alerts';
  banner.innerHTML = '<strong>Support call alerts</strong><span class="ess-call-muted">Keep this admin page open to receive incoming-call alerts.</span><button type="button" class="ess-call-enable"></button>';
  const content = document.getElementById('content') || document.body;
  content.insertBefore(banner, content.firstChild);
  const enableButton = banner.querySelector('button');

  const backdrop = document.createElement('div');
  backdrop.className = 'ess-call-backdrop';
  backdrop.hidden = true;
  backdrop.innerHTML = '<section class="ess-call-dialog" role="dialog" aria-modal="true" aria-labelledby="ess-call-title"><h2 id="ess-call-title">Incoming support call</h2><p class="ess-call-details"></p><p class="ess-call-error" role="alert" hidden></p><div class="ess-call-actions"><button type="button" class="ess-call-answer">Accept &amp; answer</button><button type="button" class="ess-call-reject">Decline</button><button type="button" class="ess-call-dismiss">Dismiss</button></div></section>';
  document.body.appendChild(backdrop);

  function updateEnableButton() {
    enableButton.textContent = alertsEnabled ? 'Desktop alerts & sound enabled' : 'Enable desktop alerts & sound';
    enableButton.disabled = alertsEnabled;
  }

  function csrfToken() {
    const match = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  async function api(path, method, body) {
    const response = await fetch(apiRoot + path, {
      method,
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken()
      },
      body: body ? JSON.stringify(body) : undefined
    });
    const data = await response.json().catch(function () { return {}; });
    if (!response.ok) throw new Error(data.detail || 'The support call could not be updated.');
    return data;
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

  function showCall(call) {
    const detail = backdrop.querySelector('.ess-call-details');
    const error = backdrop.querySelector('.ess-call-error');
    detail.textContent = (call.mode_label || call.mode || 'Support') + ' request from ' + call.display_name
      + (call.question ? ': ' + call.question : '');
    error.hidden = true;
    backdrop.dataset.callId = call.call_id;
    backdrop.hidden = false;
  }

  function showNextCall() {
    if (busy) return;
    const call = pendingCalls.find(function (item) { return !dismissed.has(item.call_id); });
    if (call) showCall(call);
    else backdrop.hidden = true;
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
      pendingCalls.forEach(function (call) {
        if (announced.has(call.call_id)) return;
        announced.add(call.call_id);
        if (alertsEnabled && 'Notification' in window && Notification.permission === 'granted') {
          const notification = new Notification('Incoming ' + (call.mode_label || call.mode) + ' call', {
            body: call.display_name + (call.question ? ': ' + call.question : ''),
            tag: 'ess-support-call-' + call.call_id
          });
          notification.onclick = function () {
            window.focus();
            showCall(call);
            notification.close();
          };
        }
      });
      const activeId = backdrop.dataset.callId;
      if (activeId && !pendingCalls.some(function (call) { return call.call_id === activeId; })) {
        backdrop.hidden = true;
      }
      if (!pendingCalls.length) {
        dismissed.clear();
        stopRing();
        backdrop.hidden = true;
      } else {
        startRing();
        showNextCall();
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
      startRing();
    } catch (error) {
      banner.querySelector('.ess-call-muted').textContent = 'Sound could not be enabled: ' + error.message;
    }
  });

  backdrop.querySelector('.ess-call-dismiss').addEventListener('click', function () {
    dismissed.add(backdrop.dataset.callId);
    backdrop.hidden = true;
  });

  backdrop.querySelector('.ess-call-reject').addEventListener('click', async function () {
    const callId = backdrop.dataset.callId;
    if (!callId || busy) return;
    busy = true;
    try {
      await api('/admin/' + callId + '/reject/', 'POST', {});
      dismissed.add(callId);
      await poll();
    } catch (error) {
      const message = backdrop.querySelector('.ess-call-error');
      message.textContent = error.message;
      message.hidden = false;
    } finally {
      busy = false;
      showNextCall();
    }
  });

  backdrop.querySelector('.ess-call-answer').addEventListener('click', async function () {
    const callId = backdrop.dataset.callId;
    if (!callId || busy || !frontendUrl) return;
    busy = true;
    const answerButton = backdrop.querySelector('.ess-call-answer');
    answerButton.disabled = true;
    try {
      await api('/admin/' + callId + '/accept/', 'POST', {});
      const session = await api('/admin/' + callId + '/session-ticket/', 'POST', {});
      const target = new URL('/support-call/' + callId, frontendUrl);
      target.hash = new URLSearchParams({ admin_ticket: session.capability }).toString();
      window.location.assign(target.toString());
    } catch (error) {
      const message = backdrop.querySelector('.ess-call-error');
      message.textContent = error.message;
      message.hidden = false;
      answerButton.disabled = false;
      await poll();
    } finally {
      busy = false;
    }
  });

  updateEnableButton();
  void poll();
  window.setInterval(poll, 5000);
})();
