"""Locating an application's stored documents.

Finding a Learning Agreement version or the transcript within an
application is the same work whoever is asking, so it lives here once.
Deciding *which* applications the caller may reach is not: that stays
with each role's service, which is why these take an application the
caller has already been granted rather than an id.

The original upload filename is not persisted, so a download name is
derived from the version and the stored extension.  That is more use to
whoever downloads it than the collision-resistant name on disk.
"""

import os

from ..errors import AppError


def learning_agreement(application, version_number):
    """The requested Learning Agreement version."""
    try:
        wanted = int(version_number)
    except (TypeError, ValueError):
        raise AppError("LEARNING_AGREEMENT_NOT_FOUND")

    for agreement in application.learning_agreements:
        if agreement.version_number == wanted:
            return agreement

    raise AppError("LEARNING_AGREEMENT_NOT_FOUND")


def transcript(application):
    # A distinct code from the ``MISSING_TRANSCRIPT`` that blocks closure:
    # there, a missing transcript is a state conflict the office must wait
    # out; here it is simply a document that does not exist yet.
    if application.transcript is None:
        raise AppError("TRANSCRIPT_NOT_FOUND")

    return application.transcript


def learning_agreement_filename(agreement) -> str:
    extension = os.path.splitext(agreement.file_path)[1]

    return f"learning-agreement-v{agreement.version_number}{extension}"


def transcript_filename(application) -> str:
    extension = os.path.splitext(application.transcript.file_path)[1]

    return f"transcript-of-records-{application.application_id}{extension}"
