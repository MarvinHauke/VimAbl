"""
Validation package for event argument validation.

This package provides schema definitions and validators to ensure
event arguments from Ableton Live conform to expected formats.
"""

from .validators import (
    ValidationError,
    ValidationResult,
    validate_event_args,
    validate_required_keys,
    validate_type,
    validate_range,
    validate_index,
    safe_get,
)
from .schemas import EVENT_SCHEMAS, EventSchema

__all__ = [
    "ValidationError",
    "ValidationResult",
    "validate_event_args",
    "validate_required_keys",
    "validate_type",
    "validate_range",
    "validate_index",
    "safe_get",
    "EVENT_SCHEMAS",
    "EventSchema",
]
