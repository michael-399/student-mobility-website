"""Helpers shared by services.

The legacy backend accepted array fields (examMappings, examMappingDiff,
examScores) either as native structures or as JSON-encoded strings inside
multipart form data, and parsed them defensively (falling back to an empty
list on malformed JSON).  ``parse_json_field`` reproduces that behaviour.
"""

import json
from typing import Any


def parse_json_field(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return default
    return value
