import {
  onAuthStateChanged,
  signOut,
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";
import { renderBarChart, initFirebaseAuth } from "./utils.js";

const loading = document.getElementById("loading");
const account = document.getElementById("account");
const userEmail = document.getElementById("userEmail");
const resultsEl = document.getElementById("results");
const noResults = document.getElementById("noResults");
const signOutBtn = document.getElementById("signOutBtn");

function renderResults(benchmark) {
  const entries = Object.entries(benchmark || {});
  if (entries.length === 0) {
    noResults.classList.remove("hidden");
    return;
  }
  // Highest percentile first, mirroring the results screen ordering.
  entries.sort((a, b) => (b[1] ?? 0) - (a[1] ?? 0));
  renderBarChart(resultsEl, entries, (pct) => `${pct}%`);
}

async function init() {
  const auth = await initFirebaseAuth();
  if (!auth) {
    loading.textContent = "Sign-in is not configured on this server yet.";
    return;
  }

  signOutBtn.addEventListener("click", async () => {
    await signOut(auth);
    window.location.href = "/login";
  });

  onAuthStateChanged(auth, async (user) => {
    if (!user) {
      window.location.href = "/login";
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
