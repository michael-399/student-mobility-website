"""Small helpers shared by the route blueprints."""

import os

from flask import request, send_file, session

from ..errors import AppError

# Multipart field names used when a file is submitted alongside JSON data.
FILE_FIELD = "file"
COURSE_MAPPINGS_FIELD = "course_mappings"


def current_user_id():
    """The signed-in user's id.

    Only called from views behind ``login_required`` or ``role_required``,
    which have already established that the session holds a real user.
    """
    return session["user_id"]


def json_body() -> dict:
    """The request's JSON body, or an empty dict.

    Services decide what is required, so a missing or unparseable body
    becomes an empty dict here and comes back as their own validation
    error rather than a generic 400 from Flask.
    """
    return request.get_json(silent=True) or {}


def uploaded_file():
    """The uploaded file, or ``None`` when the field is absent or empty."""
    file = request.files.get(FILE_FIELD)

    if file is None or not file.filename:
        return None

    return file


def send_stored_file(stored_path: str, download_name: str):
    """Return a stored document as a download.

    The path comes from a row the caller has already been authorised to
    read, never from the request, so there is nothing to sanitise -- but
    a row can outlive its file (a lost volume, a restored backup), and
    that must not surface as a 500.
    """
    absolute_path = os.path.abspath(stored_path)

    if not os.path.isfile(absolute_path):
        raise AppError("FILE_MISSING_FROM_STORAGE")

    return send_file(
        absolute_path,
        as_attachment=True,
        download_name=download_name,
    )
