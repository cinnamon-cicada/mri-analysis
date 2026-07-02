/* Shared frontend helpers */

// --- Error message boxes ---
export function showError(el, msg) {
  el.textContent = msg;
  el.classList.remove("hidden");
}

export function hideError(el) {
  el.classList.add("hidden");
}

// --- Firebase auth ---
// The SDK is imported lazily so pages that never sign in (home, data) don't
// pull it just by importing this module. Returns null if the server hasn't
// been configured with Firebase; callers own the failure UI.
export async function initFirebaseAuth() {
  const res = await fetch("/api/firebase-config");
  if (!res.ok) return null;
  const { initializeApp } = await import(
    "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js"
  );
  const { getAuth } = await import(
    "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js"
  );
  return getAuth(initializeApp(await res.json()));
}

// --- Percentile bar chart ---
// rows: iterable of [label, value] where value is a 0..1 fraction (or null).
// formatValue(pct) renders the trailing label for a 0..100 percentile.
export function renderBarChart(container, rows, formatValue) {
  container.innerHTML = "";
  for (const [label, value] of rows) {
    const pct = value == null ? null : Math.round(value * 100);
    const tier =
      pct == null ? "low" : pct >= 66 ? "high" : pct >= 33 ? "mid" : "low";
    const display = pct == null ? "—" : formatValue(pct);
    const row = document.createElement("div");
    row.className = "bar-row";
    row.innerHTML = `
      <span class="bar-label" title="${label}">${label}</span>
      <div class="bar-track"><div class="bar-fill ${tier}" style="width:${pct ?? 0}%"></div></div>
      <span class="bar-value">${display}</span>`;
    container.appendChild(row);
  }
}
