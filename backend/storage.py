"""
Storage abstraction for job files and metadata.

Local backend (default) — in-memory jobs + local filesystem.
Firebase backend — Firebase Storage for files, Firestore for job metadata.

Switch by setting STORAGE_BACKEND=firebase and providing:
  FIREBASE_STORAGE_BUCKET, GOOGLE_APPLICATION_CREDENTIALS
"""
import json
import os
from abc import ABC, abstractmethod
from pathlib import Path


class StorageBackend(ABC):
    @abstractmethod
    def store_file(self, job_id: str, data: bytes) -> str:
        """Persist uploaded file; return an opaque file reference."""

    @abstractmethod
    def load_file(self, file_ref: str) -> bytes:
        """Retrieve file by the reference returned from store_file."""

    @abstractmethod
    def get_job(self, job_id: str) -> dict | None:
        """Return job metadata, or None if not found."""

    @abstractmethod
    def set_job(self, job_id: str, data: dict) -> None:
        """Merge fields into job metadata (does not clobber unset fields)."""

    @abstractmethod
    def get_results(self, job_id: str) -> dict | None:
        """Return completed job results, or None."""

    @abstractmethod
    def set_results(self, job_id: str, data: dict) -> None:
        """Write completed job results."""

    @abstractmethod
    def count_active_jobs(self) -> int:
        """Count jobs whose status is 'queued' or 'processing'."""

    @abstractmethod
    def get_user(self, uid: str) -> dict | None:
        """Return the user record (keyed by Firebase uid), or None."""

    @abstractmethod
    def set_user(self, uid: str, data: dict) -> None:
        """Merge fields into the user record (creates it if absent)."""


_ACTIVE_STATUSES = ("queued", "processing")


class LocalStorage(StorageBackend):
    """In-process backend for local development. Not safe for multi-process deployments."""

    def __init__(
        self,
        upload_dir: str = "uploads",
        results_dir: str = "results",
    ):
        self._upload_dir = Path(upload_dir)
        self._results_dir = Path(results_dir)
        self._upload_dir.mkdir(parents=True, exist_ok=True)
        self._results_dir.mkdir(parents=True, exist_ok=True)
        self._jobs: dict = {}
        self._users: dict = {}

    def store_file(self, job_id: str, data: bytes) -> str:
        path = self._upload_dir / f"{job_id}.nii.gz"
        path.write_bytes(data)
        return str(path)

    def load_file(self, file_ref: str) -> bytes:
        return Path(file_ref).read_bytes()

    def get_job(self, job_id: str) -> dict | None:
        return self._jobs.get(job_id)

    def set_job(self, job_id: str, data: dict) -> None:
        self._jobs.setdefault(job_id, {}).update(data)

    def get_results(self, job_id: str) -> dict | None:
        path = self._results_dir / f"{job_id}.json"
        return json.loads(path.read_text()) if path.exists() else None

    def set_results(self, job_id: str, data: dict) -> None:
        path = self._results_dir / f"{job_id}.json"
        path.write_text(json.dumps(data))

    def count_active_jobs(self) -> int:
        return sum(1 for job in self._jobs.values() if job.get("status") in _ACTIVE_STATUSES)

    def get_user(self, uid: str) -> dict | None:
        return self._users.get(uid)

    def set_user(self, uid: str, data: dict) -> None:
        self._users.setdefault(uid, {}).update(data)


class FirebaseStorage(StorageBackend):
    """
    Firebase backend. Requires firebase-admin in requirements and:
      FIREBASE_STORAGE_BUCKET  — e.g. your-project.appspot.com
      GOOGLE_APPLICATION_CREDENTIALS — path to service-account JSON
    """

    def __init__(self):
        import firebase_admin
        from firebase_admin import credentials, firestore
        from firebase_admin import storage as fb_storage

        if not firebase_admin._apps:
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred, {
                "storageBucket": os.environ["FIREBASE_STORAGE_BUCKET"]
            })
        self._db = firestore.client()
        self._bucket = fb_storage.bucket()

    def store_file(self, job_id: str, data: bytes) -> str:
        blob = self._bucket.blob(f"uploads/{job_id}.nii.gz")
        blob.upload_from_string(data, content_type="application/gzip")
        return blob.name

    def load_file(self, file_ref: str) -> bytes:
        return self._bucket.blob(file_ref).download_as_bytes()

    def get_job(self, job_id: str) -> dict | None:
        doc = self._db.collection("jobs").document(job_id).get()
        return doc.to_dict() if doc.exists else None

    def set_job(self, job_id: str, data: dict) -> None:
        self._db.collection("jobs").document(job_id).set(data, merge=True)

    def get_results(self, job_id: str) -> dict | None:
        doc = self._db.collection("results").document(job_id).get()
        return doc.to_dict() if doc.exists else None

    def set_results(self, job_id: str, data: dict) -> None:
        self._db.collection("results").document(job_id).set(data)

    def count_active_jobs(self) -> int:
        query = self._db.collection("jobs").where("status", "in", list(_ACTIVE_STATUSES))
        result = query.count().get()
        return result[0][0].value

    def get_user(self, uid: str) -> dict | None:
        doc = self._db.collection("users").document(uid).get()
        return doc.to_dict() if doc.exists else None

    def set_user(self, uid: str, data: dict) -> None:
        self._db.collection("users").document(uid).set(data, merge=True)


_backend: StorageBackend | None = None


def get_storage() -> StorageBackend:
    global _backend
    if _backend is None:
        if os.environ.get("STORAGE_BACKEND") == "firebase":
            _backend = FirebaseStorage()
        else:
            _backend = LocalStorage()
    return _backend
