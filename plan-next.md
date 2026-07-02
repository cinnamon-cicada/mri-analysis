# Plan — Next Steps (Brain Benchmark MRI)

Supersedes the forward-looking parts of `plan.txt` (kept for history only;
its project id `brainbenchmark-mri`, "Docker not installed" note, and Phase 4
commands are all stale — see CLAUDE.md / `bin/deploy.sh` for correct values).

## Where we are now (all committed, tested — 37 pass)

- **Worker fixed for Cloud Run**: FastSurfer runs natively in-container
  (`FASTSURFER_MODE=native`), license mounted as a secret file. Dockerfiles +
  worker Job manifest corrected.
- **Firebase Auth accounts** live: `/login`, `/self`, `users` store,
  `GET /api/me`, `GET /api/firebase-config`, job→user results linkage.
- **Firebase project configured**: Web App registered, Email/Password provider
  enabled, web config wired into `mri-api` env. Verified end-to-end with a real
  token (signup → `/api/me` → 401 on bogus). Test user cleaned up.
- **Hosting routing fixed**: `/api/**` rewrite + `cleanUrls` so the multi-page
  app resolves in production.
- **Deploy is ready but NOT run** — no images built, nothing on Cloud Run yet.
  `bin/deploy.sh` holds the corrected commands.

---

## Phase A — Pre-deploy hardening (quick, do before building images)

1. **Pin Starlette** (and tighten FastAPI) in `requirements.txt`. Today
   `fastapi>=0.110.0` with no `starlette` pin — this is exactly how a breaking
   Starlette change silently reached the repo before (the `TemplateResponse`
   500). Pin so the production image is reproducible.
2. **Add route smoke tests** for `GET /`, `/data`, `/login`, `/self` returning
   200 (only `/login` and `/self` are covered now). Cheap guard against the
   template-signature class of bug that already shipped a live 500 once.

## Phase B — Deploy (Phase 4), STAGED — billable + outward-facing, needs go-ahead

Run `bin/deploy.sh` stage by stage, with a checkpoint after the worker image,
because the **native FastSurfer path has never run against the real
`deepmi/fastsurfer` image** (couldn't introspect the multi-GB base locally):

1. Build the **API** image (`gcloud builds submit … Dockerfile.api`).
2. Build the **worker** image, then **smoke-test it**: start a manual
   `mri-worker` execution on a tiny scan and confirm `run_fastsurfer.sh` is
   found and launches (validates `FASTSURFER_HOME`/entrypoint-reset
   assumptions). Fix `FASTSURFER_RUN_SCRIPT`/`ENTRYPOINT` if needed.
3. Deploy worker Job, dispatcher Function, API Service, then Firebase Hosting
   (rules/indexes/storage/hosting).
4. Grant the API `run.invoker` if Hosting 403s (commented in `deploy.sh`).

## Phase C — Post-deploy verification

- `curl https://<mri-api>/healthz` → ok.
- Upload 3 scans back-to-back → confirm via Firestore only 2 ever reach
  `processing` (dispatcher 2-slot cap); 6th while 5 active → 503 toast.
- **Browser auth flow** on the Hosting URL: sign up, land on `/self`, sign out,
  redirect to `/login`. (Only the token path is machine-verified so far.)
- End-to-end: upload a real T1w → status polls to `completed` (multi-hour) →
  results render, and — for a signed-in user — appear on `/self`.

## Phase D — Product completeness (post-deploy, optional/parallel)

1. **`/home` routing split** (plan.txt 1L-ii, not done): move the upload flow
   off `/` onto `/home`, make `/` a landing page or redirect. DECISION NEEDED —
   currently `/` still serves the uploader; confirm if the split is still
   wanted.
2. **Raw region stats on `/self`** (plan.txt 1L-iii): the user record stores
   `benchmark_results` (percentiles) but not raw region volumes, because
   `compare_to_benchmark()` only returns percentiles. Surface raw measurements
   from `analysis.py` if the flat `{region: value}` map is still wanted.
3. **`/self` polish**: surface an in-progress job's status/link, and handle the
   "uploaded but not yet complete" state (right now `/self` only shows finished
   results or "no results yet").

## Phase E — Docs & hygiene

1. **Update CLAUDE.md** — it documents zero auth/accounts. Add: `auth.py`, the
   `users` collection, `/api/me` + `/api/firebase-config`, job `uid` +
   `attach_results_to_user`, and the `FIREBASE_API_KEY/AUTH_DOMAIN/APP_ID` env
   vars. The next session needs this.
2. **Retire/annotate `plan.txt`** as historical; this file is the live plan.
3. **Confirm Firestore rules** for `users` — currently deny-all (correct: the
   backend uses the Admin SDK and clients never read Firestore directly). Just
   document the decision so it isn't mistaken for an omission.
4. **Authorized domains** reminder: default covers Hosting domains; add the
   `*.run.app` or any custom domain to Auth → Authorized domains if the app is
   ever served outside Firebase Hosting.

---

## Recommended order

Phase A (fast, ~30 min) → Phase B staged with the worker-image checkpoint →
Phase C → then Phase E docs → Phase D as product priorities dictate.
Everything except Phase B is safe to do without deploying.
