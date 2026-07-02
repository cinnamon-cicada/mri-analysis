"""
Firebase ID token verification for protected endpoints.

The browser signs in with the Firebase JS SDK (see frontend/login.js) and sends
the resulting ID token as `Authorization: Bearer <token>`. We verify it
server-side with firebase-admin. This shares a single firebase_admin app with
the Firebase storage backend (storage.py); whichever initializes first wins,
and both pass FIREBASE_STORAGE_BUCKET so the app is configured consistently.

Requires application-default credentials (GOOGLE_APPLICATION_CREDENTIALS), the
same as STORAGE_BACKEND=firebase.
"""
import os

from fastapi import HTTPException


def _ensure_firebase_app() -> None:
    import firebase_admin
    from firebase_admin import credentials

    if firebase_admin._apps:
        return
    options = {}
    bucket = os.environ.get("FIREBASE_STORAGE_BUCKET")
    if bucket:
        options["storageBucket"] = bucket
    firebase_admin.initialize_app(credentials.ApplicationDefault(), options)


def verify_bearer_token(authorization: str | None) -> dict:
    """Verify an `Authorization: Bearer <id_token>` header.

    Returns the decoded token claims (includes `uid` and, usually, `email`).
    Raises HTTP 401 if the header is missing/malformed or the token fails
    verification (bad signature, expired, wrong audience, etc.).
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.split(" ", 1)[1].strip()

    _ensure_firebase_app()
    from firebase_admin import auth as fb_auth

    try:
        return fb_auth.verify_id_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="invalid or expired token")
