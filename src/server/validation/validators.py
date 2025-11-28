"""
Event argument validators.

This module provides validation functions to ensure event arguments
conform to expected schemas and types.
"""

from typing import Any, Dict, List, Tuple, Optional
import logging

from .schemas import EVENT_SCHEMAS, EventSchema

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when event argument validation fails."""
    pass


class ValidationResult:
    """Result of validation with detailed error information."""

    def __init__(self, valid: bool, errors: List[str] = None):
        self.valid = valid
        self.errors = errors or []

    def __bool__(self):
        return self.valid

    def __str__(self):
        if self.valid:
            return "Validation passed"
        return f"Validation failed: {'; '.join(self.errors)}"


def validate_event_args(event_type: str, event_args: Dict[str, Any]) -> ValidationResult:
    """
    Validate event arguments against schema.

    Args:
        event_type: Type of event (e.g., "track_added")
        event_args: Arguments to validate

    Returns:
        ValidationResult with success status and any errors

    Example:
        >>> result = validate_event_args("track_added", {"track_index": 0})
        >>> if result.valid:
        ...     # Process event
        ... else:
        ...     logger.error(result.errors)
    """
    schema = EVENT_SCHEMAS.get(event_type)

    if schema is None:
        # No schema defined - allow all arguments
        logger.debug(f"No schema defined for event type: {event_type}")
        return ValidationResult(valid=True)

    errors = []

    # Check required arguments
    missing = [key for key in schema.required if key not in event_args]
    if missing:
        errors.append(f"Missing required arguments: {', '.join(missing)}")

    # Check types for present arguments
    for key, value in event_args.items():
        expected_type = schema.types.get(key)
        if expected_type and not isinstance(value, expected_type):
            errors.append(
                f"Argument '{key}' has type {type(value).__name__}, "
                f"expected {expected_type.__name__}"
            )

    # Check for unknown arguments (optional - log warning only)
    all_known = set(schema.required) | set(schema.optional)
    unknown = [key for key in event_args.keys() if key not in all_known]
    if unknown:
        logger.warning(
            f"Unknown arguments for {event_type}: {', '.join(unknown)}"
        )

    return ValidationResult(valid=len(errors) == 0, errors=errors)


def validate_required_keys(event_args: Dict[str, Any], *keys: str) -> Tuple[bool, Optional[str]]:
    """
    Simple validation to check if required keys are present.

    Args:
        event_args: Arguments to validate
        *keys: Required key names

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        >>> valid, error = validate_required_keys(args, "track_index", "device_index")
        >>> if not valid:
        ...     return EventResult.error(error)
    """
    missing = [key for key in keys if key not in event_args]

    if missing:
        error_msg = f"Missing required arguments: {', '.join(missing)}"
        return False, error_msg

    return True, None


def validate_type(value: Any, expected_type: type, field_name: str = None) -> Tuple[bool, Optional[str]]:
    """
    Validate that a value is of expected type.

    Args:
        value: Value to validate
        expected_type: Expected type
        field_name: Optional field name for error message

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        >>> valid, error = validate_type(track_idx, int, "track_index")
        >>> if not valid:
        ...     return EventResult.error(error)
    """
    if not isinstance(value, expected_type):
        field_label = f"'{field_name}'" if field_name else "Value"
        error_msg = (
            f"{field_label} has type {type(value).__name__}, "
            f"expected {expected_type.__name__}"
        )
        return False, error_msg

    return True, None


def validate_range(value: float, min_val: float = None, max_val: float = None,
                   field_name: str = None) -> Tuple[bool, Optional[str]]:
    """
    Validate that a numeric value is within a range.

    Args:
        value: Value to validate
        min_val: Minimum value (inclusive), None for no minimum
        max_val: Maximum value (inclusive), None for no maximum
        field_name: Optional field name for error message

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        >>> valid, error = validate_range(volume, 0.0, 1.0, "volume")
        >>> if not valid:
        ...     return EventResult.error(error)
    """
    field_label = f"'{field_name}'" if field_name else "Value"

    if min_val is not None and value < min_val:
        return False, f"{field_label} {value} is below minimum {min_val}"

    if max_val is not None and value > max_val:
        return False, f"{field_label} {value} exceeds maximum {max_val}"

    return True, None


def validate_index(index: int, field_name: str = None) -> Tuple[bool, Optional[str]]:
    """
    Validate that an index is non-negative.

    Args:
        index: Index to validate
        field_name: Optional field name for error message

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        >>> valid, error = validate_index(track_idx, "track_index")
        >>> if not valid:
        ...     return EventResult.error(error)
    """
    # First check it's an int
    valid, error = validate_type(index, int, field_name)
    if not valid:
        return valid, error

    # Then check range
    return validate_range(index, min_val=0, field_name=field_name)


def safe_get(event_args: Dict[str, Any], key: str, default: Any = None,
             expected_type: type = None) -> Any:
    """
    Safely get a value from event_args with optional type validation.

    Args:
        event_args: Arguments dictionary
        key: Key to retrieve
        default: Default value if key not present
        expected_type: Optional type to validate against

    Returns:
        Value from dict or default

    Example:
        >>> track_idx = safe_get(event_args, "track_index", 0, int)
        >>> device_name = safe_get(event_args, "device_name", "Unknown", str)
    """
    value = event_args.get(key, default)

    if expected_type is not None and value is not None:
        if not isinstance(value, expected_type):
            logger.warning(
                f"Key '{key}' has type {type(value).__name__}, "
                f"expected {expected_type.__name__}, using default"
            )
            return default

    return value
