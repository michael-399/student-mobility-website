"""Helpers shared by services.

Course mappings are submitted alongside the Learning Agreement file, so
they arrive as a JSON-encoded string inside multipart form data rather
than as a parsed JSON body.  ``parse_json_field`` decodes such a field
and falls back to a default when it is absent or malformed, leaving the
caller to decide whether an empty result is an error.
"""

import json
from datetime import date, datetime
from typing import Any


def parse_date(value: Any) -> date | None:
    """Coerce an ISO date string to a ``date``.

    Returns ``None`` for an absent or empty value so callers can tell
    "not supplied" apart from a real date.  A malformed string raises,
    because silently discarding a date the student did supply would hide
    the mistake behind a successful response.
    """
    if value is None or value == "":
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    return date.fromisoformat(str(value))


def parse_json_field(value: Any, default: Any) -> Any:
    if value is None:
        return default

    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return default

    return value
