"""Startup guards for production-readiness preconditions that only a human
can actually satisfy (e.g. signing a legal agreement), but that code can at
least refuse to silently run without.
"""
import os


def check_hipaa_baa_confirmed() -> None:
    """Refuse to start against the Firebase backend unless someone has
    explicitly attested the Google Cloud BAA is in place.

    This can't verify a BAA actually exists -- only the GCP console can --
    it just stops the app from silently serving real uploads against
    Firestore/Cloud Storage before anyone has confirmed the BAA covering
    them has been executed.
    """
    if os.environ.get("STORAGE_BACKEND") != "firebase":
        return
    if os.environ.get("HIPAA_BAA_CONFIRMED", "").lower() != "true":
        raise RuntimeError(
            "STORAGE_BACKEND=firebase requires HIPAA_BAA_CONFIRMED=true. "
            "Confirm the Google Cloud BAA (covering Firestore, Cloud Storage, "
            "and Firebase Auth) has been executed in the GCP console, then set "
            "this env var before starting the app."
        )
