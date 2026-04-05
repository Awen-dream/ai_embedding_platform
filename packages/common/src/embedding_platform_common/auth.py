from __future__ import annotations

from typing import Optional


def is_api_key_valid(expected_key: str, provided_key: Optional[str]) -> bool:
    if not expected_key:
        return True
    return provided_key == expected_key
