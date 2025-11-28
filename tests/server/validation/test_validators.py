import pytest
from src.server.validation.validators import validate_required_keys, validate_type, validate_range, validate_index, safe_get

def test_validate_required_keys_with_valid_args():
    """
    Test validate_required_keys with all required keys present.
    """
    event_args = {"track_index": 0, "device_index": 1}
    is_valid, error_message = validate_required_keys(event_args, "track_index", "device_index")
    assert is_valid is True
    assert error_message is None

def test_validate_required_keys_with_missing_keys():
    """
    Test validate_required_keys with some required keys missing.
    """
    event_args = {"track_index": 0}
    is_valid, error_message = validate_required_keys(event_args, "track_index", "device_index")
    assert is_valid is False
    assert "Missing required arguments: device_index" in error_message

def test_validate_required_keys_with_no_keys_required():
    """
    Test validate_required_keys when no keys are required.
    """
    event_args = {"track_index": 0, "device_index": 1}
    is_valid, error_message = validate_required_keys(event_args)
    assert is_valid is True
    assert error_message is None

def test_validate_required_keys_with_empty_args_and_required_keys():
    """
    Test validate_required_keys with empty event_args and required keys.
    """
    event_args = {}
    is_valid, error_message = validate_required_keys(event_args, "track_index", "device_index")
    assert is_valid is False
    assert "Missing required arguments: track_index, device_index" in error_message

def test_validate_type_with_correct_type():
    """
    Test validate_type with a correct type.
    """
    is_valid, error_message = validate_type(123, int, "test_field")
    assert is_valid is True
    assert error_message is None

def test_validate_type_with_incorrect_type():
    """
    Test validate_type with an incorrect type.
    """
    is_valid, error_message = validate_type(123, str, "test_field")
    assert is_valid is False
    assert "test_field' has type int, expected str" in error_message

def test_validate_type_with_no_field_name():
    """
    Test validate_type without a field name.
    """
    is_valid, error_message = validate_type("hello", str)
    assert is_valid is True
    assert error_message is None

def test_validate_type_with_none_value_and_type():
    """
    Test validate_type with None value and a specified type.
    This should return False as None is not an instance of int.
    """
    is_valid, error_message = validate_type(None, int, "test_field")
    assert is_valid is False
    assert "'test_field' has type NoneType, expected int" in error_message

def test_validate_type_with_float_for_int_expected():
    """
    Test validate_type with a float value when int is expected.
    """
    is_valid, error_message = validate_type(1.0, int, "test_field")
    assert is_valid is False
    assert "'test_field' has type float, expected int" in error_message


def test_validate_range_within_valid_range():
    """
    Test validate_range with a value within the valid range.
    """
    is_valid, error_message = validate_range(0.5, 0.0, 1.0, "test_field")
    assert is_valid is True
    assert error_message is None

def test_validate_range_below_minimum():
    """
    Test validate_range with a value below the minimum.
    """
    is_valid, error_message = validate_range(-0.1, 0.0, 1.0, "test_field")
    assert is_valid is False
    assert "'test_field' -0.1 is below minimum 0.0" in error_message

def test_validate_range_above_maximum():
    """
    Test validate_range with a value above the maximum.
    """
    is_valid, error_message = validate_range(1.1, 0.0, 1.0, "test_field")
    assert is_valid is False
    assert "'test_field' 1.1 exceeds maximum 1.0" in error_message

def test_validate_range_no_min_value():
    """
    Test validate_range with no minimum value specified.
    """
    is_valid, error_message = validate_range(10.0, max_val=100.0, field_name="test_field")
    assert is_valid is True
    assert error_message is None

def test_validate_range_no_max_value():
    """
    Test validate_range with no maximum value specified.
    """
    is_valid, error_message = validate_range(50.0, min_val=0.0, field_name="test_field")
    assert is_valid is True
    assert error_message is None

def test_validate_range_at_minimum_boundary():
    """
    Test validate_range with a value at the minimum boundary.
    """
    is_valid, error_message = validate_range(0.0, 0.0, 1.0, "test_field")
    assert is_valid is True
    assert error_message is None

def test_validate_range_at_maximum_boundary():
    """
    Test validate_range with a value at the maximum boundary.
    """
    is_valid, error_message = validate_range(1.0, 0.0, 1.0, "test_field")
    assert is_valid is True
    assert error_message is None




def test_validate_index_valid_non_negative_index():
    """
    Test validate_index with a valid non-negative index.
    """
    is_valid, error_message = validate_index(0, "track_index")
    assert is_valid is True
    assert error_message is None

def test_validate_index_negative_index_should_fail():
    """
    Test validate_index with a negative index, which should fail.
    """
    is_valid, error_message = validate_index(-1, "track_index")
    assert is_valid is False
    assert "'track_index' -1 is below minimum 0" in error_message

def test_validate_index_with_non_integer_value():
    """
    Test validate_index with a non-integer value.
    """
    is_valid, error_message = validate_index(0.5, "track_index")
    assert is_valid is False
    assert "'track_index' has type float, expected int" in error_message

def test_validate_index_with_none_value():
    """
    Test validate_index with None value.
    """
    is_valid, error_message = validate_index(None, "track_index")
    assert is_valid is False
    assert "'track_index' has type NoneType, expected int" in error_message


def test_safe_get_with_existing_key():
    """
    Test safe_get with an existing key.
    """
    event_args = {"track_index": 5}
    value = safe_get(event_args, "track_index", 0, int)
    assert value == 5

def test_safe_get_with_default_value():
    """
    Test safe_get with a missing key, expecting the default value.
    """
    event_args = {}
    value = safe_get(event_args, "track_index", 0, int)
    assert value == 0

def test_safe_get_with_type_mismatch():
    """
    Test safe_get with a key present but with a type mismatch.
    It should return the default value and log a warning.
    """
    event_args = {"track_index": "not_an_int"}
    # We expect a warning to be logged, but for now we just check the return value
    value = safe_get(event_args, "track_index", 0, int)
    assert value == 0

def test_safe_get_with_no_expected_type():
    """
    Test safe_get without specifying an expected type.
    """
    event_args = {"track_name": "Audio 1"}
    value = safe_get(event_args, "track_name", "Unknown")
    assert value == "Audio 1"

def test_safe_get_with_none_value_and_expected_type():
    """
    Test safe_get with a key whose value is None, and an expected type.
    It should return None as the default if None is the actual value, and not cause a type error.
    """
    event_args = {"optional_param": None}
    value = safe_get(event_args, "optional_param", 0, int)
    assert value is None

def test_safe_get_with_none_value_and_no_expected_type():
    """
    Test safe_get with a key whose value is None, and no expected type.
    """
    event_args = {"optional_param": None}
    value = safe_get(event_args, "optional_param", 0)
    assert value is None

def test_safe_get_key_not_present_no_default_no_type():
    """
    Test safe_get when key is not present, no default, and no type.
    """
    event_args = {}
    value = safe_get(event_args, "non_existent_key")
    assert value is None

