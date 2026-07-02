import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import {
  getAuth,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";

const form = document.getElementById("authForm");
const emailInput = document.getElementById("email");
const passwordInput = document.getElementById("password");
const submitBtn = document.getElementById("submitBtn");
const title = document.getElementById("authTitle");
const togglePrompt = document.getElementById("togglePrompt");
const toggleLink = document.getElementById("toggleLink");
const errorBox = document.getElementById("authError");

let mode = "signin"; // or "signup"
let auth = null;

function showError(msg) {
  errorBox.textContent = msg;
  errorBox.classList.remove("hidden");
}

function clearError() {
  errorBox.classList.add("hidden");
}

async function init() {
  const res = await fetch("/api/firebase-config");
  if (!res.ok) {
    form.classList.add("hidden");
    toggleLink.classList.add("hidden");
    showError("Sign-in is not configured on this server yet.");
    return;
  }
  const config = await res.json();
  auth = getAuth(initializeApp(config));
}

function setMode(next) {
  mode = next;
  clearError();
  if (mode === "signup") {
    title.textContent = "Create account";
    submitBtn.textContent = "Create account";
    togglePrompt.textContent = "Already have an account?";
    toggleLink.textContent = "Sign in";
    passwordInput.autocomplete = "new-password";
  } else {
    title.textContent = "Sign in";
    submitBtn.textContent = "Sign in";
    togglePrompt.textContent = "Don't have an account?";
    toggleLink.textContent = "Create one";
    passwordInput.autocomplete = "current-password";
  }
}

toggleLink.addEventListener("click", (e) => {
  e.preventDefault();
  setMode(mode === "signin" ? "signup" : "signin");
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!auth) return;
  clearError();
  submitBtn.disabled = true;
  const email = emailInput.value.trim();
  const password = passwordInput.value;
  try {
    if (mode === "signup") {
      await createUserWithEmailAndPassword(auth, email, password);
    } else {
      await signInWithEmailAndPassword(auth, email, password);
    }
    window.location.href = "/self";
  } catch (err) {
    showError(err.message || "Authentication failed.");
    submitBtn.disabled = false;
  }
});

init();
