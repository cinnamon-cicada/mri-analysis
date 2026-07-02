/* Population statistics page — segment dropdown + count-distribution histogram */

import { showError as showErrorBox, hideError } from './utils.js';

const segmentSelect = document.getElementById('segmentSelect');
const histogramEl = document.getElementById('histogram');
const histError = document.getElementById('histError');
const histCaption = document.getElementById('histCaption');
const histYMax = document.getElementById('histYMax');
const histYMin = document.getElementById('histYMin');
const histXMin = document.getElementById('histXMin');
const histXMax = document.getElementById('histXMax');

async function loadSegments() {
  try {
    const res = await fetch('/api/population/segments');
    if (!res.ok) throw new Error(`Failed to load segments (${res.status})`);
    const segments = await res.json();

    segmentSelect.innerHTML = segments
      .map(s => `<option value="${s.key}">${s.label}</option>`)
      .join('');

    if (segments.length) loadDistribution(segments[0].key);
  } catch (err) {
    showError(err.message);
  }
}

async function loadDistribution(segment) {
  hideError(histError);
  try {
    const res = await fetch(`/api/population/distribution/${encodeURIComponent(segment)}`);
    if (!res.ok) throw new Error(`Failed to load distribution (${res.status})`);
    const data = await res.json();
    renderHistogram(data);
  } catch (err) {
    showError(err.message);
  }
}

function renderHistogram(data) {
  histogramEl.innerHTML = '';
  const max = Math.max(...data.counts, 1);

  data.counts.forEach((count, i) => {
    const lo = data.edges[i];
    const hi = data.edges[i + 1];
    const bar = document.createElement('div');
    bar.className = 'hist-bar';
    bar.style.height = `${(count / max) * 100}%`;
    bar.title = `${lo.toFixed(1)}–${hi.toFixed(1)}: ${count}`;
    histogramEl.appendChild(bar);
  });

  histYMax.textContent = max;
  histYMin.textContent = '0';
  histXMin.textContent = data.edges[0].toFixed(1);
  histXMax.textContent = data.edges[data.edges.length - 1].toFixed(1);

  histCaption.textContent = `n = ${data.n} subjects`;
}

function showError(msg) {
  histogramEl.innerHTML = '';
  for (const el of [histYMax, histYMin, histXMin, histXMax]) el.textContent = '';
  showErrorBox(histError, msg);
}

segmentSelect.addEventListener('change', () => loadDistribution(segmentSelect.value));

loadSegments();
