# Privacy Policy

**The Brain Benchmark Project**
Last updated: 2026-07-01

## 1. Overview

This Privacy Policy explains how The Brain Benchmark Project ("we", "us") collects, uses, stores, and protects information submitted through this Service, with particular attention to the sensitive nature of neuroimaging data.

## 2. What We Collect

| Data Type | Purpose | Retention |
|-----------|---------|-----------|
| Uploaded MRI/NIfTI files | Brain scan processing | Deleted within 30 days |
| Job metadata (job ID, status, timestamps) | Pipeline tracking | 90 days |
| IP address | Rate limiting and abuse prevention | 24 hours in memory |
| Derived volumetric statistics | Statistical comparison results | Up to 1 year (anonymized) |

We do not collect names, email addresses, or account information unless you voluntarily provide them.

## 3. Neuroimaging Data — Special Category

Brain MRI data is considered **sensitive personal data** under many jurisdictions (including GDPR Article 9 and HIPAA). We treat all uploaded scan files with the following protections:

- Files are encrypted in transit (TLS) and at rest (Google Cloud Storage server-side encryption)
- Access is restricted to automated processing pipelines; no human reviews raw scan files except in verified incident response scenarios
- Raw scan files are never shared with third parties
- Files are deleted on schedule and are not used to train machine learning models without explicit, informed consent

## 4. How We Use Your Data

- **Processing**: Uploaded scans are processed by the FastSurfer/FreeSurfer pipeline to extract volumetric brain measurements
- **Comparison**: Measurements are compared against an anonymized population reference dataset
- **Abuse prevention**: IP addresses are used solely for rate limiting the upload endpoint
- **Research** (opt-in only): Anonymized, aggregated volumetric statistics may be used to improve reference norms. This never includes raw scan files

## 5. Data Sharing

We do not sell, rent, or share your data with third parties except:
- **Google Cloud Platform**: Infrastructure provider for storage and compute (governed by Google's Data Processing Addendum)
- **Legal obligation**: If required by valid legal process, we will notify you to the extent permitted by law

## 6. Your Rights

Depending on your jurisdiction, you may have rights to:
- **Access**: Request a copy of data we hold about you
- **Deletion**: Request immediate deletion of your uploaded files and derived results
- **Correction**: Request correction of inaccurate data
- **Portability**: Receive your results in a machine-readable format

To exercise any of these rights, contact: mashiur10.khan@vanderbilt.edu

## 7. Children's Privacy

The Service is not directed at individuals under 18. We do not knowingly collect neuroimaging data from minors without verifiable parental or guardian consent and appropriate institutional approval.

## 8. Research and IRB

If you are uploading data collected under an Institutional Review Board (IRB) protocol, ensure that your consent forms and data sharing approvals cover use of this Service. We are not responsible for ensuring compliance with your institution's IRB requirements.

## 9. Security

We use industry-standard safeguards including encrypted storage, least-privilege IAM service accounts, and rate-limited API endpoints. However, no system is completely secure. In the event of a data breach affecting your uploaded neuroimaging data, we will notify affected users within 72 hours in accordance with applicable law.

## 10. Changes to This Policy

We will post any material changes to this page and update the "Last updated" date. We encourage you to review this policy periodically.

## 11. Contact

Privacy inquiries and deletion requests: mashiur10.khan@vanderbilt.edu
