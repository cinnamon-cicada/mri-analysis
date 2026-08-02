# Incident Response Plan — The Brain Benchmark Project

Based on [NIST SP 800-61](https://csrc.nist.gov/pubs/sp/800/61/r2/final) (Computer Security Incident Handling Guide), scoped to this project's actual stack: FastAPI on Cloud Run, Firestore, GCS, a Cloud Run Job worker, and a Cloud Functions dispatcher. This document exists specifically to back the commitment in `legal/privacy-policy.md` §9: *"In the event of a data breach affecting your uploaded neuroimaging data, we will notify affected users within 72 hours."* Before this document, that promise had no operational process behind it — see risk R6 in `security/risk-register.md`.

Solo-maintainer note: there is one incident commander — the project maintainer (mashiur10.khan@vanderbilt.edu) — until this project has more than one person on it. Adjust the roles section below the day that changes.

## Roles

- **Incident Commander**: the maintainer. Owns the decision to declare an incident, drives containment, and owns the 72-hour notification clock.
- **Escalation contacts**: Vanderbilt IRB liaison (if the incident involves data uploaded under an IRB protocol per `legal/privacy-policy.md` §8) and institutional legal counsel, as applicable to the specific incident.

## 1. Preparation (standing controls, not incident-time steps)

- Structured logging in `backend/auth.py`, `app.py`, `worker.py` → Cloud Logging.
- Data Access audit logs enabled on the scans GCS bucket and Firestore.
- Cloud Monitoring alert policies for `SetIamPolicy`, `CreateServiceAccountKey`, Data Access read spikes, repeated auth failures (`infra/monitoring/setup-alerts.sh`).
- This document, reviewed quarterly and after any tabletop exercise finds a gap.

## 2. Detection & Analysis

**Entry points**: a Cloud Monitoring alert fires, Sentry reports an anomalous exception pattern, a Prowler scan finds a new critical misconfiguration, or a manual report (e.g. a user email).

**On any of the above**, the Incident Commander:

1. **Confirm it's real.** Check the relevant Cloud Logging query (see "Useful queries" below) to distinguish a genuine incident from a false alarm (e.g. a legitimate key rotation triggering the `CreateServiceAccountKey` alert).
2. **Timestamp "discovery."** This is what starts the 72-hour clock for §9 — the moment a human confirms unauthorized access/disclosure of scan data occurred, not the moment an alert fired.
3. **Scope it.** Determine which `job_id`s / `uid`s are affected using the audit trail (queries below). This is the step Track B's Data Access audit logs exist to make possible — without them this step cannot be done reliably.

**Useful queries** (run via `gcloud logging read` or the Cloud Console Logs Explorer):

```bash
# Who accessed a specific scan file / job's data in GCS
gcloud logging read '
  resource.type="gcs_bucket"
  AND protoPayload.resourceName:"<file_ref or job_id>"
' --project=the-brain-benchmark-project --freshness=30d

# Firestore reads/writes on a specific job doc
gcloud logging read '
  resource.type="firestore_instance"
  AND protoPayload.resourceName:"jobs/<job_id>"
' --project=the-brain-benchmark-project --freshness=30d

# Recent IAM policy changes (who granted/changed access to what)
gcloud logging read '
  protoPayload.methodName="SetIamPolicy"
' --project=the-brain-benchmark-project --freshness=30d

# Recently created service account keys (possible credential exfiltration prep)
gcloud logging read '
  protoPayload.methodName="google.iam.admin.v1.CreateServiceAccountKey"
' --project=the-brain-benchmark-project --freshness=30d

# Application-level failed-auth / forbidden-access events (once Track B logging lands)
gcloud logging read '
  resource.type="cloud_run_revision"
  AND jsonPayload.event=~"auth_failed|forbidden_job_access"
' --project=the-brain-benchmark-project --freshness=30d
```

## 3. Containment

Pick the action(s) that match the incident:

**Leaked/compromised service-account key** (`service-account-key.json` or any other SA key):

```bash
# List keys for the affected SA
gcloud iam service-accounts keys list --iam-account=<sa-email> --project=the-brain-benchmark-project

# Delete the compromised key immediately
gcloud iam service-accounts keys delete <KEY_ID> --iam-account=<sa-email> --project=the-brain-benchmark-project

# If the SA itself is fully compromised, disable it while investigating
gcloud iam service-accounts disable <sa-email> --project=the-brain-benchmark-project
```

**Compromised Firebase Admin credentials**:

```bash
# Generate a fresh key for mri-api-sa
gcloud iam service-accounts keys create ./new-service-account-key.json \
  --iam-account=mri-api-sa@the-brain-benchmark-project.iam.gserviceaccount.com

# Delete the old key (see list/delete commands above)
# Update GOOGLE_APPLICATION_CREDENTIALS wherever it's deployed (Cloud Run env/secret), then redeploy
```

**Overly broad or unexpected IAM grant**:

```bash
# Inspect current policy
gcloud projects get-iam-policy the-brain-benchmark-project

# Remove a specific binding
gcloud projects remove-iam-policy-binding the-brain-benchmark-project \
  --member="<member>" --role="<role>"
```

**Abuse via the public API** (e.g. upload flooding, scraping `/status`): the existing `slowapi` rate limit (5/min/IP on `/upload`) and the 5-active-job capacity cap are the first line of defense; for a sustained attack, temporarily block the source at the load balancer / Cloud Armor, or scale down `count_active_jobs()`'s threshold.

## 4. Eradication & Recovery

- Confirm the containment action actually closed the hole (re-run the relevant audit-log query and confirm no further unauthorized activity).
- Rotate any other credential that shared exposure context with the compromised one.
- Restore normal service (re-enable the SA, redeploy with fresh credentials, lift any temporary blocks).

## 5. Post-Incident — Notification & Write-Up

- **If the incident involved unauthorized access to or disclosure of uploaded scan data**: draft and send the breach notification to affected users, **within 72 hours of the discovery timestamp from step 2**. Use the scoped `job_id`/`uid` list from the Analysis step to identify who to notify; anonymous (no-`uid`) jobs have no notification path by design (no collected contact info), which is itself worth noting in the write-up if it applies.
- File a write-up as a closed GitHub issue using the `security-incident` template (`.github/ISSUE_TEMPLATE/security-incident.md`), including: timeline, root cause, scope, containment actions taken, and at least one concrete follow-up (e.g. a new risk-register entry or a new Cloud Monitoring alert).
- Update `security/risk-register.md` if the incident exposed a risk that wasn't already tracked.

## Chain of custody for manual scan-file review

`legal/privacy-policy.md` §3 states: *"Access is restricted to automated processing pipelines; no human reviews raw scan files except in verified incident response scenarios."* Until now nothing enforced or logged that exception. Going forward:

1. Any human review of a raw scan file during an incident must be preceded by opening (or referencing) the incident's GitHub issue.
2. The issue must record: who is reviewing, which `job_id`(s), and the specific reason review is necessary for containment/analysis.
3. Only the Incident Commander (or someone they explicitly designate in the issue) may perform the review.

## Tabletop exercises

Run at least quarterly. First exercise: simulate a leaked `service-account-key.json` end-to-end (create a throwaway key, "leak" it internally, then run the full detect → contain → recover flow above) and confirm every command in this document is actually copy-pasteable and correct. Log the date and outcome here:

| Date | Scenario | Outcome | Follow-ups |
|------|----------|---------|------------|
| _(pending)_ | Leaked service-account key | | |
