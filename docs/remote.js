const buttons = [...document.querySelectorAll('[data-key]')];
const display = document.querySelector('#display');
const notice = document.querySelector('#notice');
const meter = document.querySelector('#meter');
const mode = document.querySelector('#mode');
const help = document.querySelector('#help');
let learned = null;
let standby = false;
let muted = false;
let volume = 35;

document.querySelector('#setup').onclick = () => help.showModal();

for (let index = 0; index < 20; index++) {
  meter.append(document.createElement('span'));
}

function drawMeter(level) {
  [...meter.children].forEach((bar, index) => {
    bar.classList.toggle('lit', index < Math.ceil(level / 5));
  });
}

function simulate(button) {
  const key = button.dataset.key;
  if (key === 'power') standby = !standby;
  if (key === 'mute' && !standby) {
    muted = !muted;
    button.setAttribute('aria-pressed', muted);
  }
  if (key.startsWith('volume_') && !standby) {
    volume = Math.max(0, Math.min(100, volume + (key === 'volume_up' ? 5 : -5)));
  }
  if (!standby && button.closest('.lower .row:not(.extras)')) {
    for (const peer of button.parentElement.children) {
      peer.setAttribute('aria-pressed', peer === button);
    }
  }
  drawMeter(standby || muted ? 0 : volume);
  if (standby) return 'STANDBY';
  if (key.startsWith('volume_')) return 'VOL ' + String(volume).padStart(2, '0');
  if (key === 'mute') return muted ? 'MUTED' : 'UNMUTED';
  if (key === 'power') return 'POWER ON';
  return button.textContent.trim().toUpperCase();
}

async function configure() {
  buttons.forEach(button => { button.disabled = true; });
  try {
    const response = await fetch('./api/status', {cache: 'no-store', signal: AbortSignal.timeout(2500)});
    if (response.ok) {
      const status = await response.json();
      if (Array.isArray(status.learned)) learned = new Set(status.learned);
    }
  } catch {
    // Static hosting and offline previews run in demo mode.
  }
  mode.textContent = learned ? 'IR BRIDGE' : 'DEMO MODE';
  mode.closest('.screen-top').classList.toggle('live', Boolean(learned));
  notice.textContent = learned
    ? `${learned.size} buttons learned. IR commands are one-way.`
    : 'Try the controls in demo mode. Open Setup to connect your soundbar.';
  if (!learned) drawMeter(volume);
  buttons.forEach(button => { button.disabled = false; });
}

async function send(button) {
  const key = button.dataset.key;
  if (!learned) {
    display.textContent = simulate(button);
    return;
  }
  if (!learned.has(key)) {
    notice.textContent = 'Teach the bridge this button first. See Setup.';
    return;
  }
  buttons.forEach(item => { item.disabled = true; });
  try {
    const response = await fetch('./api/send', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({key}),
      signal: AbortSignal.timeout(8000)
    });
    if (!response.ok) throw new Error('Transmission failed');
    display.textContent = 'IR SENT';
    notice.textContent = `Sent ${button.getAttribute('aria-label') || button.textContent.trim()}.`;
  } catch {
    display.textContent = 'SEND ERROR';
    notice.textContent = 'Check the bridge and blaster connection, then try again.';
  } finally {
    buttons.forEach(item => { item.disabled = false; });
    button.focus({preventScroll: true});
  }
}

buttons.forEach(button => button.addEventListener('click', () => send(button)));
configure();
