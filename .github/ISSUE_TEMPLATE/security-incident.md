---
name: Security incident
about: Track a suspected or confirmed security incident, per security/incident-response-plan.md
title: "[INCIDENT] "
labels: incident, security
assignees: ''
---

<!-- See security/incident-response-plan.md for the full process. This issue IS the case record. -->

## Discovery

- **Detected via**: (Cloud Monitoring alert / Sentry / Prowler scan / manual report / other)
- **Discovery timestamp** (starts the 72h clock if scan data was accessed/disclosed): 
- **Reported by**: 

## Scope

- **Affected `job_id`(s)**: 
- **Affected `uid`(s)**: 
- **Audit-log queries run** (paste query + summary of findings):

## Containment actions taken

- [ ] Compromised credential(s) revoked/rotated (list which)
- [ ] IAM policy changes reviewed/reverted
- [ ] Other:

## Manual scan-file review log (if applicable)

Per the chain-of-custody section of the IR plan — any human review of raw scan files during this incident must be logged here before it happens.

| Who | job_id(s) | Reason | Timestamp |
|-----|-----------|--------|-----------|
|     |           |        |           |

## Notification (if scan data was accessed/disclosed without authorization)

- [ ] Affected users notified within 72 hours of discovery timestamp
- **Notification sent at**: 

## Post-incident

- **Root cause**: 
- **Follow-ups** (new risk-register entries, new alerts, code fixes):
