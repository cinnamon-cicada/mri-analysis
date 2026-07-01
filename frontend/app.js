/* MRI Brain Analysis — frontend logic */

const POLL_INTERVAL_MS = 5000;

// --- Screen transitions ---
function show(screenId) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(screenId).classList.add('active');
}

// --- File drop zone ---
const dropZone  = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const dropLabel = document.getElementById('dropLabel');
const uploadBtn = document.getElementById('uploadBtn');
const uploadError = document.getElementById('uploadError');

fileInput.addEventListener('change', () => onFileSelected(fileInput.files[0]));

dropZone.addEventListener('dragover', e => {
  e.preventDefault();
  dropZone.classList.add('dragover');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  onFileSelected(e.dataTransfer.files[0]);
});

function onFileSelected(file) {
  if (!file) return;
  const ok = file.name.endsWith('.nii') || file.name.endsWith('.nii.gz');
  dropLabel.textContent = file.name;
  uploadBtn.disabled = !ok;
  if (!ok) showError('Only .nii or .nii.gz files are accepted.');
  else clearError();
}

function showError(msg) {
  uploadError.textContent = msg;
  uploadError.classList.remove('hidden');
}
function clearError() {
  uploadError.classList.add('hidden');
}

// --- Upload ---
uploadBtn.addEventListener('click', async () => {
  const file = fileInput.files[0];
  if (!file) return;

  clearError();
  uploadBtn.disabled = true;

  const formData = new FormData();
  formData.append('file', file);

  let jobId;
  try {
    const res = await fetch('/upload', { method: 'POST', body: formData });
    if (!res.ok) throw new Error(`Upload failed (${res.status})`);
    const data = await res.json();
    jobId = data.job_id;
  } catch (err) {
    showError(err.message);
    uploadBtn.disabled = false;
    return;
  }

  document.getElementById('jobIdDisplay').textContent = `Job ID: ${jobId}`;
  show('screen-processing');
  pollStatus(jobId);
});

// --- Status polling ---
function pollStatus(jobId) {
  const msgEl = document.getElementById('processingMsg');
  const statuses = {
    queued:     'Your scan is queued for analysis. This typically takes 10–30 minutes.',
    processing: 'FastSurfer is running on your scan…',
  };

  const timer = setInterval(async () => {
    try {
      const res = await fetch(`/status/${jobId}`);
      const data = await res.json();

      if (statuses[data.status]) {
        msgEl.textContent = statuses[data.status];
      }

      if (data.status === 'completed') {
        clearInterval(timer);
        await loadResults(jobId);
      } else if (data.status === 'failed') {
        clearInterval(timer);
        show('screen-upload');
        showError(`Analysis failed: ${data.error || 'unknown error'}`);
        uploadBtn.disabled = false;
      }
    } catch (_) {
      // network hiccup — keep polling
    }
  }, POLL_INTERVAL_MS);
}

// --- Results ---
async function loadResults(jobId) {
  const res = await fetch(`/results/${jobId}`);
  const data = await res.json();
  renderChart('chart-volumes', data.volume_percentiles || []);
  renderChart('chart-thickness', data.thickness_percentiles || []);
  show('screen-results');
}

function renderChart(containerId, rows) {
  const container = document.getElementById(containerId);
  container.innerHTML = '';

  if (!rows.length) {
    container.textContent = 'No data available.';
    return;
  }

  rows.forEach(([label, value]) => {
    const pct = value == null ? null : Math.round(value * 100);
    const displayPct = pct == null ? '—' : `${pct}th`;
    const fillPct = pct ?? 0;
    const tier = pct == null ? '' : pct >= 70 ? 'high' : pct >= 30 ? 'mid' : 'low';

    const row = document.createElement('div');
    row.className = 'bar-row';
    row.innerHTML = `
      <span class="bar-label" title="${label}">${label}</span>
      <div class="bar-track">
        <div class="bar-fill ${tier}" style="width:${fillPct}%"></div>
      </div>
      <span class="bar-value">${displayPct}</span>
    `;
    container.appendChild(row);
  });
}

// --- Tabs ---
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));
    tab.classList.add('active');
    document.getElementById(`tab-${tab.dataset.tab}`).classList.remove('hidden');
  });
});

// --- Restart ---
document.getElementById('restartBtn').addEventListener('click', () => {
  fileInput.value = '';
  dropLabel.textContent = 'Drop your .nii.gz file here, or click to browse';
  uploadBtn.disabled = true;
  clearError();
  show('screen-upload');
});
