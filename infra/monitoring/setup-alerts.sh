#!/usr/bin/env bash
# Creates log-based metrics + Cloud Monitoring alert policies for the
# high-risk events called out in security/risk-register.md (R9) and
# security/incident-response-plan.md:
#   - SetIamPolicy (IAM policy changed)
#   - CreateServiceAccountKey (new SA key minted — possible exfil prep)
#   - Data Access read spikes on the scans GCS bucket
#   - Repeated application-level auth failures (backend/auth.py `auth_failed`)
#
# NOT run automatically. This makes live changes to a real GCP project and
# creates a billing-relevant (though free-tier, at current scale) Cloud
# Monitoring notification channel. Review before running.
#
# Prereqs:
#   - `gcloud` authenticated with an account that has roles/monitoring.editor
#     and roles/logging.admin (or equivalent) on the project.
#   - Data Access audit logs enabled on the scans bucket/Firestore first —
#     otherwise the Data Access log-based metric below will never match
#     anything. See the IAM audit-config step at the bottom of this script.
#
# Usage:
#   NOTIFY_EMAIL=you@example.com PROJECT_ID=the-brain-benchmark-project \
#     BUCKET_NAME=<scans-bucket-name> ./infra/monitoring/setup-alerts.sh --confirm
#
# Omit --confirm to print what would run without applying anything.

set -euo pipefail

PROJECT_ID="${PROJECT_ID:-the-brain-benchmark-project}"
NOTIFY_EMAIL="${NOTIFY_EMAIL:?Set NOTIFY_EMAIL to the address that should receive alerts}"
BUCKET_NAME="${BUCKET_NAME:?Set BUCKET_NAME to the scans GCS bucket name}"
CONFIRM=false
[[ "${1:-}" == "--confirm" ]] && CONFIRM=true

run() {
  echo "+ $*"
  if $CONFIRM; then
    "$@"
  fi
}

if ! $CONFIRM; then
  echo "Dry run — pass --confirm to actually apply. Showing commands only."
fi

# ── Notification channel ─────────────────────────────────────────────────
run gcloud alpha monitoring channels create \
  --project="$PROJECT_ID" \
  --display-name="mri-analysis security alerts" \
  --type=email \
  --channel-labels=email_address="$NOTIFY_EMAIL"

echo "NOTE: copy the channel ID printed above into CHANNEL_ID below, then re-run"
echo "the alert-policy commands, or fetch it first with:"
echo "  gcloud alpha monitoring channels list --project=$PROJECT_ID --filter='displayName=\"mri-analysis security alerts\"' --format='value(name)'"

# ── Log-based metrics ────────────────────────────────────────────────────
run gcloud logging metrics create iam_policy_changes \
  --project="$PROJECT_ID" \
  --description="SetIamPolicy calls — see security/incident-response-plan.md" \
  --log-filter='protoPayload.methodName="SetIamPolicy"'

run gcloud logging metrics create sa_key_created \
  --project="$PROJECT_ID" \
  --description="New service-account keys minted — see security/incident-response-plan.md" \
  --log-filter='protoPayload.methodName="google.iam.admin.v1.CreateServiceAccountKey"'

run gcloud logging metrics create scans_bucket_read_spike \
  --project="$PROJECT_ID" \
  --description="GCS object reads on the scans bucket — requires Data Access audit logs enabled first" \
  --log-filter="resource.type=\"gcs_bucket\" AND resource.labels.bucket_name=\"$BUCKET_NAME\" AND protoPayload.methodName=\"storage.objects.get\""

run gcloud logging metrics create app_auth_failures \
  --project="$PROJECT_ID" \
  --description="backend/auth.py structured auth_failed events, from Cloud Run stdout logs" \
  --log-filter='resource.type="cloud_run_revision" AND jsonPayload.event="auth_failed"'

# ── Alert policies ───────────────────────────────────────────────────────
# CHANNEL_ID: fill in from the `channels list` command above before running
# the block below with --confirm.
CHANNEL_ID="${CHANNEL_ID:-projects/$PROJECT_ID/notificationChannels/REPLACE_ME}"

make_policy() {
  local display_name="$1" metric="$2" threshold="$3"
  cat <<JSON
{
  "displayName": "$display_name",
  "combiner": "OR",
  "conditions": [{
    "displayName": "$display_name",
    "conditionThreshold": {
      "filter": "resource.type=\"global\" AND metric.type=\"logging.googleapis.com/user/$metric\"",
      "comparison": "COMPARISON_GT",
      "thresholdValue": $threshold,
      "duration": "0s",
      "aggregations": [{"alignmentPeriod": "300s", "perSeriesAligner": "ALIGN_COUNT"}]
    }
  }],
  "notificationChannels": ["$CHANNEL_ID"]
}
JSON
}

for spec in \
  "IAM policy changed:iam_policy_changes:0" \
  "New service-account key created:sa_key_created:0" \
  "Scans bucket read spike:scans_bucket_read_spike:50" \
  "Repeated auth failures:app_auth_failures:10"
do
  IFS=":" read -r name metric threshold <<< "$spec"
  policy_file="$(mktemp)"
  make_policy "$name" "$metric" "$threshold" > "$policy_file"
  run gcloud alpha monitoring policies create --project="$PROJECT_ID" --policy-from-file="$policy_file"
  rm -f "$policy_file"
done

# ── Data Access audit logs (prerequisite for scans_bucket_read_spike) ────
# This is a project-level IAM audit config change, done separately since it
# affects log volume/Cloud Logging billing project-wide (see risk-register.md
# R9 for the free-tier math). Uncomment and run deliberately:
#
# cat > /tmp/audit-policy.yaml <<'YAML'
# auditConfigs:
# - service: storage.googleapis.com
#   auditLogConfigs:
#   - logType: DATA_READ
# - service: firestore.googleapis.com
#   auditLogConfigs:
#   - logType: DATA_READ
#   - logType: DATA_WRITE
# YAML
# gcloud projects get-iam-policy "$PROJECT_ID" --format=yaml > /tmp/current-policy.yaml
# # Merge /tmp/audit-policy.yaml into /tmp/current-policy.yaml's auditConfigs by hand, then:
# gcloud projects set-iam-policy "$PROJECT_ID" /tmp/current-policy.yaml
