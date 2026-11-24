'use strict';

const $ = (id) => document.getElementById(id);
const SVGNS = 'http://www.w3.org/2000/svg';

let network = null;
let latest = null;
let history = [];
let selected = null;

const colorFor = (c) => (c < 35 ? 'var(--free)' : c < 65 ? 'var(--mod)' : 'var(--heavy)');
const el = (name, attrs = {}) => {
  const e = document.createElementNS(SVGNS, name);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  return e;
};

// ---------- Map ----------
function buildMap() {
  const svg = $('map');
  svg.innerHTML = '';
  const pos = Object.fromEntries(network.nodes.map((n) => [n.id, n]));
  network.edges.forEach(([a, b]) => {
    svg.appendChild(el('line', { class: 'edge', 'data-a': a, 'data-b': b, x1: pos[a].x, y1: pos[a].y, x2: pos[b].x, y2: pos[b].y, stroke: 'var(--border)' }));
  });
  network.nodes.forEach((n) => {
    const g = el('g', { class: 'node', 'data-id': n.id });
    g.appendChild(el('circle', { class: 'pulse', cx: n.x, cy: n.y, r: 3.5, style: 'display:none' }));
    g.appendChild(el('circle', { class: 'ring', cx: n.x, cy: n.y, r: 4.4 }));
    g.appendChild(el('circle', { class: 'core', cx: n.x, cy: n.y, r: 3.2, fill: 'var(--muted)' }));
    const t = el('text', { x: n.x, y: n.y + 7.2 });
    t.textContent = n.name;
    g.appendChild(t);
    g.addEventListener('click', () => { selected = selected === n.id ? null : n.id; render(); });
    svg.appendChild(g);
  });
}

function updateMap() {
  const byId = Object.fromEntries(latest.nodes.map((n) => [n.id, n]));
  const incNodes = new Set(latest.incidents.map((i) => i.nodeId));
  document.querySelectorAll('#map .node').forEach((g) => {
    const id = g.dataset.id;
    g.querySelector('.core').setAttribute('fill', colorFor(byId[id].congestion));
    g.querySelector('.pulse').style.display = incNodes.has(id) ? '' : 'none';
    g.classList.toggle('sel', id === selected);
  });
  document.querySelectorAll('#map .edge').forEach((e) => {
    const c = Math.max(byId[e.dataset.a].congestion, byId[e.dataset.b].congestion);
    e.setAttribute('stroke', colorFor(c));
  });
}

// ---------- Chart ----------
function path(points, w, h, min, max) {
  const n = points.length;
  return points
    .map((v, i) => {
      const x = (i / Math.max(1, n - 1)) * w;
      const y = h - ((v - min) / (max - min)) * h;
      return (i ? 'L' : 'M') + x.toFixed(1) + ' ' + y.toFixed(1);
    })
    .join(' ');
}

function updateChart() {
  const svg = $('chart');
  const W = 400, H = 180;
  svg.innerHTML = '';
  for (let i = 1; i < 4; i++) {
    svg.appendChild(el('line', { x1: 0, x2: W, y1: (H / 4) * i, y2: (H / 4) * i, stroke: 'var(--border)', 'stroke-width': 1, 'vector-effect': 'non-scaling-stroke' }));
  }
  if (history.length < 2) return;
  const speed = history.map((h) => h.speed);
  const cong = history.map((h) => h.congestion);
  svg.appendChild(el('path', { d: path(speed, W, H, 0, 60), fill: 'none', stroke: 'var(--accent)', 'stroke-width': 2, 'vector-effect': 'non-scaling-stroke' }));
  svg.appendChild(el('path', { d: path(cong, W, H, 0, 100), fill: 'none', stroke: 'var(--heavy)', 'stroke-width': 2, 'vector-effect': 'non-scaling-stroke' }));
}

// ---------- Table & incidents ----------
function updateTable() {
  const info = Object.fromEntries(network.nodes.map((n) => [n.id, n]));
  const rows = [...latest.nodes].sort((a, b) => b.congestion - a.congestion);
  $('rows').innerHTML = rows
    .map(
      (n) => `<tr class="${n.id === selected ? 'sel' : ''}" data-id="${n.id}">
        <td>${info[n.id].name}</td>
        <td><span class="bar"><span style="width:${n.congestion}%;background:${colorFor(n.congestion)}"></span></span>${n.congestion}</td>
        <td>${n.speed} km/h</td>
        <td>${n.vehicles}</td>
        <td><span class="sig">${n.signal.phase} green &middot; ${n.signal.remaining}s</span></td>
      </tr>`
    )
    .join('');
  document.querySelectorAll('#rows tr').forEach((tr) =>
    tr.addEventListener('click', () => { selected = selected === tr.dataset.id ? null : tr.dataset.id; render(); })
  );
}

const ago = (ts) => {
  const s = Math.max(0, Math.round((Date.now() - ts) / 1000));
  return s < 60 ? `${s}s ago` : `${Math.round(s / 60)}m ago`;
};

function updateIncidents() {
  const list = latest.incidents;
  $('incidents').innerHTML = list.length
    ? list
        .map((i) => `<li class="sev${i.severity}"><div class="t">${i.type}</div><div class="m">${i.node} &middot; severity ${i.severity}/3 &middot; ${ago(i.startedAt)}</div></li>`)
        .join('')
    : '<li class="empty" style="border:none;background:none">No active incidents</li>';
}

function updateKpis() {
  const k = latest.kpis;
  $('k-speed').textContent = k.avgSpeed;
  $('k-cong').textContent = k.congestion;
  $('k-veh').textContent = k.vehicles.toLocaleString();
  $('k-inc').textContent = k.activeIncidents;
  $('k-worst').textContent = `worst: ${k.worst.name} (${k.worst.congestion})`;
  $('mode').value = latest.mode;
}

function render() {
  if (!latest || !network) return;
  updateKpis();
  updateMap();
  updateChart();
  updateTable();
  updateIncidents();
}

// ---------- Data ----------
function setStatus(on) {
  const s = $('status');
  s.textContent = on ? 'live' : 'reconnecting…';
  s.className = 'pill ' + (on ? 'pill-on' : 'pill-off');
}

function onSnapshot(snap) {
  latest = snap;
  history.push({ t: snap.ts, speed: snap.kpis.avgSpeed, congestion: snap.kpis.congestion });
  if (history.length > 120) history.shift();
  $('clock').textContent = new Date(snap.ts).toLocaleTimeString();
  render();
}

async function init() {
  network = await (await fetch('/api/network')).json();
  history = await (await fetch('/api/history')).json();
  buildMap();

  const es = new EventSource('/api/stream');
  es.onopen = () => setStatus(true);
  es.onerror = () => setStatus(false);
  es.onmessage = (e) => onSnapshot(JSON.parse(e.data));

  $('mode').addEventListener('change', (e) =>
    fetch('/api/mode', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ mode: e.target.value }) })
  );
}

init().catch((err) => { console.error(err); setStatus(false); });
