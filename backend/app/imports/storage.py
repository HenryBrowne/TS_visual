"""Uploaded CSVs are stored on disk under an opaque upload_id so the
3-step interactive wizard (detect -> map -> validate) and the final
commit (POST /api/jobs/ingest-and-profile) can all reference the same
file without re-uploading it on every step.
"""

import uuid
from pathlib import Path

from app.core.paths import DATA_UPLOADS_DIR


def save_upload(filename: str, content: bytes) -> str:
    DATA_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    upload_id = str(uuid.uuid4())
    suffix = Path(filename).suffix or ".csv"
    (DATA_UPLOADS_DIR / f"{upload_id}{suffix}").write_bytes(content)
    return upload_id


def get_upload_path(upload_id: str) -> Path:
    matches = list(DATA_UPLOADS_DIR.glob(f"{upload_id}.*"))
    if not matches:
        raise KeyError(f"Unknown upload_id: {upload_id}")
    return matches[0]
