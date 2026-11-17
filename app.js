(() => {
'use strict';

const tg = window.Telegram && window.Telegram.WebApp;
if (tg) {
  try { tg.ready(); tg.expand(); tg.setHeaderColor('#0b1020'); tg.setBackgroundColor('#0b1020'); } catch (e) {}
}
const $ = (s) => document.querySelector(s);
const TAU = Math.PI * 2;
const mod = (a, m) => ((a % m) + m) % m;
const faNum = (n) => Number(n).toLocaleString('fa-IR');

const state = {
  names: [], winners: [], settings: { auto_remove: false }, limits: { max_names: 100, max_len: 30 },
  spinning: false, rotation: 0, drawSegs: null, editingId: null, owner: false, version: 0, spinSeq: 0,
};

/* ---------- helpers ---------- */
let toastTimer;
function toast(msg) {
  const t = $('#toast'); t.textContent = msg; t.classList.add('show');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.remove('show'), 2600);
}
function haptic(kind, style) {
  try {
    const h = tg && tg.HapticFeedback; if (!h) return;
    if (kind === 'impact') h.impactOccurred(style || 'light');
    else if (kind === 'notify') h.notificationOccurred(style || 'success');
  } catch (e) {}
}
function confirmBox(msg, cb) {
  if (tg && tg.showConfirm) tg.showConfirm(msg, (ok) => ok && cb());
  else if (window.confirm(msg)) cb();
}
async function api(path, body) {
  let data, status = 0;
  try {
    const res = await fetch('/api/' + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Init-Data': tg ? tg.initData : '' },
      body: JSON.stringify(body || {}),
    });
    status = res.status;
    data = await res.json();
  } catch (e) { throw new Error('ارتباط با سرور برقرار نشد.'); }
  if (!data.ok) { const err = new Error(data.error || 'خطا'); err.status = status; throw err; }
  return data;
}
function el(tag, cls, text) {
  const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e;
}

/* ---------- state ---------- */
function applyState(d) {
  state.names = d.names; state.winners = d.winners; state.settings = d.settings; state.limits = d.limits;
  if (d.role) { state.owner = d.role === 'owner'; applyRole(); }
  if (d.version != null) state.version = d.version;
  if (d.spin_seq != null) state.spinSeq = d.spin_seq;
  if (state.editingId && !state.names.some((n) => n.id === state.editingId)) state.editingId = null;
  renderAll();
}
async function refresh() {
  const d = await api('state'); applyState(d);
  if (d.rotation != null && !state.spinning) { state.rotation = d.rotation; drawWheel(state.rotation); }
}
function applyRole() {
  const o = state.owner;
  ['#spinBtn', '#addCard', '#clearBtn', '#winClearBtn', '#winAgain', '#chipAuto'].forEach((s) => $(s).classList.toggle('hidden', !o));
  $('#chipRole').classList.toggle('hidden', o);
  document.querySelector('[data-tab="settings"]').classList.toggle('hidden', !o);
}

/* ---------- tabs ---------- */
document.querySelectorAll('.tab').forEach((b) => b.addEventListener('click', () => switchTab(b.dataset.tab)));
function switchTab(name) {
  document.querySelectorAll('.tab').forEach((b) => b.classList.toggle('active', b.dataset.tab === name));
  document.querySelectorAll('.view').forEach((v) => v.classList.toggle('active', v.id === 'view-' + name));
  if (name === 'wheel') requestAnimationFrame(() => { setupCanvas(); drawWheel(state.rotation); });
  haptic('impact', 'light');
}

/* ---------- rendering (lists) ---------- */
function renderAll() {
  renderWheelInfo(); renderNames(); renderWinners();
  $('#autoRemove').checked = !!state.settings.auto_remove;
  if (!state.spinning) drawWheel(state.rotation);
}
function renderWheelInfo() {
  const n = state.names.length;
  $('#chipCount').textContent = faNum(n) + ' نفر';
  $('#chipAuto').textContent = 'حذف خودکار: ' + (state.settings.auto_remove ? 'روشن' : 'خاموش');
  const hint = $('#hint');
  if (!state.owner) {
    hint.classList.remove('hidden');
    hint.textContent = n < 2 ? 'ادمین هنوز اسم‌ها را کامل نکرده است.' : '👀 منتظر چرخش ادمین باش؛ نتیجه زنده نمایش داده می‌شود.';
  } else if (n < 2) {
    hint.classList.remove('hidden');
    hint.textContent = n === 0 ? 'برای شروع، از تب «اسامی» اسم اضافه کن.' : 'حداقل دو اسم لازم است.';
  } else hint.classList.add('hidden');
  $('#spinBtn').disabled = state.spinning || n < 2;
}
function renderNames() {
  const ul = $('#nameList'); ul.textContent = '';
  $('#namesCount').textContent = faNum(state.names.length) + ' / ' + faNum(state.limits.max_names);
  if (!state.names.length) { ul.appendChild(el('li', 'empty', 'لیست خالی است')); return; }
  state.names.forEach((n, i) => {
    const li = el('li');
    li.appendChild(el('span', 'idx', faNum(i + 1)));
    if (!state.owner) { li.appendChild(el('span', 'nm', n.name)); ul.appendChild(li); return; }
    if (state.editingId === n.id) {
      const inp = el('input'); inp.type = 'text'; inp.value = n.name; inp.maxLength = state.limits.max_len;
      const ok = el('button', 'icon-btn', '✔️'); const no = el('button', 'icon-btn', '✖️');
      const save = async () => {
        try { applyState(await api('edit', { id: n.id, name: inp.value })); state.editingId = null; renderNames(); toast('ویرایش شد ✅'); }
        catch (e) { toast(e.message); }
      };
      ok.onclick = save; no.onclick = () => { state.editingId = null; renderNames(); };
      inp.addEventListener('keydown', (e) => { if (e.key === 'Enter') save(); });
      li.append(inp, ok, no); ul.appendChild(li); setTimeout(() => inp.focus(), 30);
    } else {
      const ed = el('button', 'icon-btn', '✏️'); const del = el('button', 'icon-btn', '🗑');
      ed.onclick = () => { state.editingId = n.id; renderNames(); };
      del.onclick = async () => {
        try { applyState(await api('remove', { id: n.id })); haptic('impact', 'medium'); } catch (e) { toast(e.message); }
      };
      li.append(el('span', 'nm', n.name), ed, del); ul.appendChild(li);
    }
  });
}
function renderWinners() {
  const ul = $('#winnerList'); ul.textContent = '';
  if (!state.winners.length) { ul.appendChild(el('li', 'empty', 'هنوز برنده‌ای ثبت نشده')); return; }
  state.winners.forEach((w, i) => {
    const li = el('li');
    let when = '';
    try { when = new Date(w.won_at).toLocaleString('fa-IR', { dateStyle: 'medium', timeStyle: 'short' }); } catch (e) {}
    li.append(el('span', 'idx', faNum(i + 1)), el('span', 'nm', '🏆 ' + w.name), el('span', 'when', when));
    ul.appendChild(li);
  });
}

/* ---------- actions ---------- */
$('#addBtn').addEventListener('click', async () => {
  const ta = $('#addText'); const text = ta.value.trim();
  if (!text) return toast('اسمی وارد نشده');
  const btn = $('#addBtn'); btn.disabled = true;
  try {
    const d = await api('add', { text }); applyState(d); ta.value = '';
    toast('✅ ' + faNum(d.added) + ' اسم اضافه شد' + (d.skipped ? ' (' + faNum(d.skipped) + ' اسم جا نشد)' : ''));
    haptic('notify', 'success');
  } catch (e) { toast(e.message); } finally { btn.disabled = false; }
});
$('#clearBtn').addEventListener('click', () => {
  if (!state.names.length) return toast('لیست از قبل خالی است');
  confirmBox('همه اسم‌ها پاک شوند؟', async () => {
    try { applyState(await api('clear')); toast('لیست پاک شد'); } catch (e) { toast(e.message); }
  });
});
$('#winClearBtn').addEventListener('click', () => {
  if (!state.winners.length) return toast('تاریخچه خالی است');
  confirmBox('تاریخچه برندگان پاک شود؟', async () => {
    try { applyState(await api('winners_clear')); toast('تاریخچه پاک شد'); } catch (e) { toast(e.message); }
  });
});
$('#autoRemove').addEventListener('change', async (ev) => {
  const box = ev.target;
  try { applyState(await api('settings', { auto_remove: box.checked })); toast(box.checked ? 'حذف خودکار روشن شد' : 'حذف خودکار خاموش شد'); }
  catch (e) { box.checked = !box.checked; toast(e.message); }
});

/* ---------- wheel drawing ---------- */
const canvas = $('#wheel'); const ctx = canvas.getContext('2d');
const COLORS = ['#6d5efc', '#2f6bff', '#8b5cf6', '#1f9dff', '#a855f7', '#3b82f6', '#7c3aed', '#0ea5e9', '#9333ea', '#4f46e5'];
let S = 320;
function setupCanvas() {
  S = Math.max(240, Math.min(window.innerWidth - 32, 400));
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.round(S * dpr); canvas.height = Math.round(S * dpr);
  canvas.style.width = S + 'px'; canvas.style.height = S + 'px';
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}
function drawWheel(rot) {
  const segs = state.drawSegs || state.names;
  const cx = S / 2, cy = S / 2, outerR = S / 2 - 4, ringW = 12, R = outerR - ringW;
  ctx.clearRect(0, 0, S, S);
  try { ctx.direction = 'rtl'; } catch (e) {}

  ctx.save(); ctx.shadowColor = 'rgba(124,92,255,.55)'; ctx.shadowBlur = 22;
  ctx.beginPath(); ctx.arc(cx, cy, outerR, 0, TAU); ctx.fillStyle = '#141a38'; ctx.fill(); ctx.restore();
  const g = ctx.createLinearGradient(0, 0, S, S);
  g.addColorStop(0, '#7c5cff'); g.addColorStop(.5, '#2f6bff'); g.addColorStop(1, '#a855f7');
  ctx.beginPath(); ctx.arc(cx, cy, outerR, 0, TAU); ctx.arc(cx, cy, R + 2, 0, TAU, true); ctx.fillStyle = g; ctx.fill('evenodd');
  for (let k = 0; k < 28; k++) {
    const a = (k / 28) * TAU;
    ctx.beginPath(); ctx.arc(cx + Math.cos(a) * (outerR - ringW / 2 + 1), cy + Math.sin(a) * (outerR - ringW / 2 + 1), 2, 0, TAU);
    ctx.fillStyle = k % 2 ? 'rgba(255,255,255,.95)' : 'rgba(196,181,253,.8)'; ctx.fill();
  }

  const n = segs.length;
  if (!n) {
    ctx.beginPath(); ctx.arc(cx, cy, R, 0, TAU); ctx.fillStyle = '#161c3d'; ctx.fill();
    ctx.fillStyle = '#8b93bb'; ctx.font = '600 16px Vazirmatn, Tahoma, sans-serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText('اسمی اضافه کنید', cx, cy + R * 0.35);
  } else {
    const seg = TAU / n;
    for (let i = 0; i < n; i++) {
      const a0 = -Math.PI / 2 + rot + i * seg;
      ctx.beginPath(); ctx.moveTo(cx, cy); ctx.arc(cx, cy, R, a0, a0 + seg); ctx.closePath();
      ctx.fillStyle = 'hsl(' + Math.round((230 + i * 360 / n) % 360) + ',68%,52%)'; ctx.fill();
      ctx.strokeStyle = 'rgba(255,255,255,.18)'; ctx.lineWidth = 1; ctx.stroke();
    }
    const sh = ctx.createRadialGradient(cx, cy, R * 0.1, cx, cy, R);
    sh.addColorStop(0, 'rgba(255,255,255,.14)'); sh.addColorStop(1, 'rgba(5,8,25,.32)');
    ctx.beginPath(); ctx.arc(cx, cy, R, 0, TAU); ctx.fillStyle = sh; ctx.fill();

    let fs = Math.max(9, Math.min(18, seg * R * 0.5));
    const maxW = R * 0.62;
    for (let i = 0; i < n; i++) {
      let label = segs[i].name; let size = fs;
      ctx.font = '700 ' + size + 'px Vazirmatn, Tahoma, sans-serif';
      while (ctx.measureText(label).width > maxW && size > 9) { size -= 1; ctx.font = '700 ' + size + 'px Vazirmatn, Tahoma, sans-serif'; }
      while (ctx.measureText(label).width > maxW && label.length > 3) label = label.slice(0, -2);
      if (label !== segs[i].name) label = label.trimEnd() + '…';
      ctx.save(); ctx.translate(cx, cy); ctx.rotate(-Math.PI / 2 + rot + (i + 0.5) * seg);
      ctx.fillStyle = '#fff'; ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
      ctx.shadowColor = 'rgba(0,0,0,.35)'; ctx.shadowBlur = 3;
      ctx.fillText(label, R - 14, 0); ctx.restore();
    }
  }
  // hub
  const hr = Math.max(18, R * 0.13);
  const hg = ctx.createRadialGradient(cx - 4, cy - 4, 2, cx, cy, hr);
  hg.addColorStop(0, '#2b3470'); hg.addColorStop(1, '#0d1230');
  ctx.beginPath(); ctx.arc(cx, cy, hr, 0, TAU); ctx.fillStyle = hg; ctx.fill();
  ctx.lineWidth = 3; ctx.strokeStyle = '#a78bfa'; ctx.stroke();
  ctx.font = Math.round(hr * 0.9) + 'px sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.shadowColor = 'transparent'; ctx.fillStyle = '#fff'; ctx.fillText('🌵', cx, cy + 1);
  // pointer
  ctx.save(); ctx.shadowColor = 'rgba(0,0,0,.5)'; ctx.shadowBlur = 8;
  ctx.beginPath(); ctx.moveTo(cx - 15, cy - outerR - 1); ctx.lineTo(cx + 15, cy - outerR - 1); ctx.lineTo(cx, cy - R + 24); ctx.closePath();
  const pg = ctx.createLinearGradient(0, cy - outerR, 0, cy - R + 24); pg.addColorStop(0, '#fff'); pg.addColorStop(1, '#c4b5fd');
  ctx.fillStyle = pg; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = '#4c1d95'; ctx.stroke(); ctx.restore();
}

/* ---------- spin (shared: the server plans it, everyone plays the same plan) ---------- */
let clockOffset = 0, lastSeq = 0;
const serverNow = () => Date.now() + clockOffset;
const setClock = (t) => { if (t) clockOffset = t - Date.now(); };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

$('#spinBtn').addEventListener('click', spin);
$('#winAgain').addEventListener('click', () => { closeWin(); spin(); });
$('#winClose').addEventListener('click', closeWin);
function closeWin() { $('#winOverlay').classList.add('hidden'); stopConfetti(); }

async function spin() {
  if (!state.owner || state.spinning) return;
  if (state.names.length < 2) return toast('حداقل دو اسم لازم است');
  state.spinning = true; $('#spinBtn').disabled = true; haptic('impact', 'heavy');
  let r;
  try { r = await api('spin'); }
  catch (e) { state.spinning = false; renderWheelInfo(); return toast(e.message); }
  setClock(r.server_time); lastSeq = r.event.seq;
  await playSpin(r.event);
  applyState(r);
  showWin(r.winner.name, r.removed);
}

async function playSpin(ev) {
  state.spinning = true; state.drawSegs = ev.segments; $('#spinBtn').disabled = true;
  closeWin(); switchTab('wheel');
  const seg = TAU / ev.segments.length;
  let lastTick = Math.floor(ev.r0 / seg), lastHaptic = 0;
  await new Promise((resolve) => {
    const frame = () => {
      const t = Math.min(1, Math.max(0, (serverNow() - ev.started_at) / ev.duration));
      const e = 1 - Math.pow(1 - t, 4);                  // fast start, slow stop
      const rot = ev.r0 + ev.delta * e;
      drawWheel(rot);
      const tick = Math.floor(rot / seg), now = performance.now();
      if (tick !== lastTick && now - lastHaptic > 45) { haptic('impact', t > 0.8 ? 'medium' : 'light'); lastHaptic = now; }
      lastTick = tick;
      if (t < 1) requestAnimationFrame(frame); else resolve();
    };
    requestAnimationFrame(frame);
  });
  state.rotation = mod(ev.r0 + ev.delta, TAU);
  state.drawSegs = null; state.spinning = false;
}

// viewers: ask the server once a second whether something happened
async function pollLoop() {
  for (;;) {
    await sleep(1000);
    if (state.spinning || state.owner) continue;
    try {
      const d = await api('live'); setClock(d.server_time);
      if (d.event && d.spin_seq > lastSeq) {
        const ev = d.event; lastSeq = d.spin_seq;
        if (serverNow() - ev.started_at < ev.duration + 1500) {
          await playSpin(ev); await refresh(); showWin(ev.winner.name, ev.removed);
        } else await refresh();
      } else if (d.version !== state.version) await refresh();
    } catch (e) { /* temporary network problem: try again next second */ }
  }
}

/* ---------- win overlay + confetti ---------- */
function showWin(name, removed) {
  $('#winName').textContent = name;
  $('#winNote').textContent = removed ? 'اسم برنده از لیست حذف شد.' : '';
  $('#winOverlay').classList.remove('hidden');
  haptic('notify', 'success'); startConfetti();
}
const cv = $('#confetti'); const cc = cv.getContext('2d'); let parts = [], raf = 0;
function startConfetti() {
  cv.width = window.innerWidth; cv.height = window.innerHeight;
  const cols = ['#a78bfa', '#60a5fa', '#f0abfc', '#38bdf8', '#fde68a', '#ffffff'];
  parts = Array.from({ length: 150 }, () => ({
    x: cv.width / 2, y: cv.height * 0.4, vx: (Math.random() - 0.5) * 16, vy: -Math.random() * 15 - 4,
    w: 6 + Math.random() * 6, h: 4 + Math.random() * 6, rot: Math.random() * TAU, vr: (Math.random() - 0.5) * 0.4,
    c: cols[Math.floor(Math.random() * cols.length)], life: 140 + Math.random() * 60,
  }));
  cancelAnimationFrame(raf);
  const step = () => {
    cc.clearRect(0, 0, cv.width, cv.height);
    parts.forEach((p) => {
      p.vy += 0.35; p.x += p.vx; p.y += p.vy; p.rot += p.vr; p.life--;
      cc.save(); cc.translate(p.x, p.y); cc.rotate(p.rot); cc.globalAlpha = Math.max(0, Math.min(1, p.life / 40));
      cc.fillStyle = p.c; cc.fillRect(-p.w / 2, -p.h / 2, p.w, p.h); cc.restore();
    });
    parts = parts.filter((p) => p.life > 0 && p.y < cv.height + 40);
    if (parts.length) raf = requestAnimationFrame(step); else cc.clearRect(0, 0, cv.width, cv.height);
  };
  raf = requestAnimationFrame(step);
}
function stopConfetti() { cancelAnimationFrame(raf); cc.clearRect(0, 0, cv.width, cv.height); parts = []; }

/* ---------- init ---------- */
window.addEventListener('resize', () => { setupCanvas(); drawWheel(state.rotation); });
(async function init() {
  if (!tg || !tg.initData) { $('#blocked').classList.remove('hidden'); return; }
  setupCanvas(); drawWheel(0);
  if (document.fonts && document.fonts.load) {
    document.fonts.load('700 16px Vazirmatn').then(() => { if (!state.spinning) drawWheel(state.rotation); }).catch(() => {});
  }
  try { await refresh(); lastSeq = state.spinSeq || 0; pollLoop(); } catch (e) {
    if (e.status === 401 || e.status === 403) { $('#blocked').classList.remove('hidden'); $('#blocked p').textContent = e.message; }
    else toast(e.message);
  }
})();
})();
