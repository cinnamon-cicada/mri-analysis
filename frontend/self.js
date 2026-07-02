import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import {
  getAuth,
  onAuthStateChanged,
  signOut,
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";

const loading = document.getElementById("loading");
const account = document.getElementById("account");
const userEmail = document.getElementById("userEmail");
const resultsEl = document.getElementById("results");
const noResults = document.getElementById("noResults");
const signOutBtn = document.getElementById("signOutBtn");

function goToLogin() {
  window.location.href = "/login";
}

function renderResults(benchmark) {
  const entries = Object.entries(benchmark || {});
  if (entries.length === 0) {
    noResults.classList.remove("hidden");
    return;
  }
  // Highest percentile first, mirroring the results screen ordering.
  entries.sort((a, b) => (b[1] ?? 0) - (a[1] ?? 0));
  for (const [label, pct] of entries) {
    const value = pct == null ? null : Math.round(pct * 100);
    const cls = value == null ? "low" : value >= 66 ? "high" : value >= 33 ? "mid" : "low";
    const row = document.createElement("div");
    row.className = "bar-row";
    row.innerHTML = `
      <span class="bar-label" title="${label}">${label}</span>
      <div class="bar-track"><div class="bar-fill ${cls}" style="width:${value ?? 0}%"></div></div>
      <span class="bar-value">${value == null ? "—" : value + "%"}</span>`;
    resultsEl.appendChild(row);
  }
}

async function init() {
  const res = await fetch("/api/firebase-config");
  if (!res.ok) {
    loading.textContent = "Sign-in is not configured on this server yet.";
    return;
  }
  const auth = getAuth(initializeApp(await res.json()));

  signOutBtn.addEventListener("click", async () => {
    await signOut(auth);
    goToLogin();
  });

  onAuthStateChanged(auth, async (user) => {
    if (!user) {
      goToLogin();
      return;
    }
    try {
      const token = await user.getIdToken();
      const meRes = await fetch("/api/me", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!meRes.ok) throw new Error("Failed to load account");
      const me = await meRes.json();
      userEmail.textContent = me.email || user.email || "";
      renderResults(me.benchmark_results);
      loading.classList.add("hidden");
      account.classList.remove("hidden");
    } catch (err) {
      loading.textContent = err.message || "Failed to load your account.";
    }
  });
}

init();
