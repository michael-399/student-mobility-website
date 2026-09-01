"""Uploaded-file storage.

Learning Agreements and Transcripts of Records are uploaded as files and
only their path is persisted (``learning_agreement.file_path``,
``transcript_of_records.file_path``).  Files are written under a
collision-resistant name so two students uploading "LA.pdf" do not
overwrite each other.
"""

import os
import random
import time

from flask import current_app
from werkzeug.utils import secure_filename


def _upload_dir() -> str:
    directory = current_app.config["UPLOAD_DIR"]
    os.makedirs(directory, exist_ok=True)

    return directory


def save_upload(file) -> tuple[str, str]:
    """Persist an uploaded file.

    Returns ``(original_name, stored_relative_path)``.  The original name
    is kept so it can be offered back as the download filename; the
    stored path is what goes into the database.
    """
    original_name = secure_filename(file.filename or "")
    extension = os.path.splitext(original_name)[1]

    unique_name = f"{int(time.time() * 1000)}-{random.randint(0, 10 ** 9)}{extension}"
    stored_path = os.path.join(_upload_dir(), unique_name)

    file.save(stored_path)

    return (original_name or unique_name, stored_path)
