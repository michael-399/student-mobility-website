"""Uploaded-file storage.

Reproduces the multer disk-storage behaviour of the legacy backend:
files are written to the uploads directory under a collision-resistant
name (``<timestamp>-<random>.<ext>``) and the stored path is persisted
as ``uploads/<name>`` — matching the original ``file.path`` value.
"""

import os
import random
import time

from fastapi import UploadFile

from app.core.config import settings

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


async def save_upload(file: UploadFile) -> tuple[str, str]:
    """Persist an upload; return ``(original_name, stored_relative_path)``."""
    ext = os.path.splitext(file.filename or "")[1]
    unique = f"{int(time.time() * 1000)}-{random.randint(0, 10**9)}{ext}"
    rel_path = os.path.join(settings.UPLOAD_DIR, unique)

    contents = await file.read()
    with open(rel_path, "wb") as f:
        f.write(contents)

    return (file.filename or unique, rel_path)
