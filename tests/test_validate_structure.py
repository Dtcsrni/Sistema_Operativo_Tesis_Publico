from __future__ import annotations

from validate_structure import validate


def test_validate_structure_accepts_current_repository() -> None:
    errors = validate()
    assert errors == []
