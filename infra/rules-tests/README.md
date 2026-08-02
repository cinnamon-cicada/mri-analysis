# Firestore/Storage rules tests

Verifies `infra/firestore.rules` and `infra/storage.rules` actually enforce
deny-by-default (see risk R3 in `security/risk-register.md`). Runs against the
Firebase emulator — no real GCP project or credentials needed.

## Run locally

```bash
npm install -g firebase-tools   # if not already installed
cd infra
npm --prefix rules-tests install
firebase emulators:exec --project=mri-analysis-rules-test --only firestore,storage "npm --prefix rules-tests test"
```

Runs automatically in `.github/workflows/ci.yml` on every push/PR.
