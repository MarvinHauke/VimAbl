import pytest
from src.server.validation.validators import validate_event_args, ValidationResult
from src.server.validation.schemas import EventSchema, EVENT_SCHEMAS

# Helper function to register a temporary schema for testing unknown event types
def register_temp_schema(event_type, schema):
    EVENT_SCHEMAS[event_type] = schema

def unregister_temp_schema(event_type):
    if event_type in EVENT_SCHEMAS:
        del EVENT_SCHEMAS[event_type]

# --- Tests for validate_event_args ---

def test_validate_event_args_track_added_valid():
    """
    Test validate_event_args for 'track_added' with valid arguments.
    """
    event_type = "track_added"
    event_args = {"track_index": 0, "track_name": "Audio 1", "track_color": 123}
    result = validate_event_args(event_type, event_args)
    assert result.valid is True
    assert result.errors == []

def test_validate_event_args_track_added_missing_required():
    """
    Test validate_event_args for 'track_added' with missing required argument.
    """
    event_type = "track_added"
    event_args = {"track_name": "Audio 1"} # track_index is missing
    result = validate_event_args(event_type, event_args)
    assert result.valid is False
    assert "Missing required arguments: track_index" in result.errors

def test_validate_event_args_track_added_incorrect_type():
    """
    Test validate_event_args for 'track_added' with incorrect type for an argument.
    """
    event_type = "track_added"
    event_args = {"track_index": "0", "track_name": "Audio 1"} # track_index should be int
    result = validate_event_args(event_type, event_args)
    assert result.valid is False
    assert "Argument 'track_index' has type str, expected int" in result.errors

def test_validate_event_args_track_added_unknown_argument():
    """
    Test validate_event_args for 'track_added' with an unknown argument.
    It should still be valid but log a warning (not checked in assert).
    """
    event_type = "track_added"
    event_args = {"track_index": 0, "track_name": "Audio 1", "unknown_key": "value"}
    result = validate_event_args(event_type, event_args)
    assert result.valid is True
    assert result.errors == []

def test_validate_event_args_unknown_event_type():
    """
    Test validate_event_args with an event type that has no defined schema.
    It should return valid=True and no errors.
    """
    event_type = "non_existent_event"
    event_args = {"some_arg": "value"}
    result = validate_event_args(event_type, event_args)
    assert result.valid is True
    assert result.errors == []

def test_validate_event_args_track_name_changed_valid():
    event_type = "track_name_changed"
    event_args = {"track_index": 0, "track_name": "New Name"}
    result = validate_event_args(event_type, event_args)
    assert result.valid is True
    assert result.errors == []

def test_validate_event_args_track_name_changed_missing_name():
    event_type = "track_name_changed"
    event_args = {"track_index": 0}
    result = validate_event_args(event_type, event_args)
    assert result.valid is False
    assert "Missing required arguments: track_name" in result.errors

def test_validate_event_args_volume_changed_valid():
    event_type = "volume_changed"
    event_args = {"track_index": 0, "volume": 0.5}
    result = validate_event_args(event_type, event_args)
    assert result.valid is True
    assert result.errors == []

def test_validate_event_args_volume_changed_incorrect_type():
    event_type = "volume_changed"
    event_args = {"track_index": 0, "volume": "half"}
    result = validate_event_args(event_type, event_args)
    assert result.valid is False
    assert "Argument 'volume' has type str, expected float" in result.errors

def test_validate_event_args_mute_changed_valid():
    event_type = "mute_changed"
    event_args = {"track_index": 0, "is_muted": True}
    result = validate_event_args(event_type, event_args)
    assert result.valid is True
    assert result.errors == []

def test_validate_event_args_arm_changed_valid():
    event_type = "arm_changed"
    event_args = {"track_index": 0, "is_armed": False}
    result = validate_event_args(event_type, event_args)
    assert result.valid is True
    assert result.errors == []


def test_validate_event_args_device_added_valid():
    """
    Test validate_event_args for 'device_added' with valid arguments.
    """
    event_type = "device_added"
    event_args = {"track_index": 0, "device_index": 0, "device_name": "EQ Eight"}
    result = validate_event_args(event_type, event_args)
    assert result.valid is True
    assert result.errors == []

def test_validate_event_args_device_added_missing_required():
    """
    Test validate_event_args for 'device_added' with missing required argument.
    """
    event_type = "device_added"
    event_args = {"track_index": 0} # device_index is missing
    result = validate_event_args(event_type, event_args)
    assert result.valid is False
    assert "Missing required arguments: device_index" in result.errors

def test_validate_event_args_device_deleted_valid():
    """
    Test validate_event_args for 'device_deleted' with valid arguments.
    """
    event_type = "device_deleted"
    event_args = {"track_index": 0, "device_index": 0}
    result = validate_event_args(event_type, event_args)
    assert result.valid is True
    assert result.errors == []

def test_validate_event_args_device_parameter_changed_valid():
    """
    Test validate_event_args for 'device_parameter_changed' with valid arguments.
    """
    event_type = "device_parameter_changed"
    event_args = {"track_index": 0, "device_index": 0, "parameter_index": 0, "parameter_value": 0.5}
    result = validate_event_args(event_type, event_args)
    assert result.valid is True
    assert result.errors == []

def test_validate_event_args_device_parameter_changed_incorrect_type():
    """
    Test validate_event_args for 'device_parameter_changed' with incorrect type.
    """
    event_type = "device_parameter_changed"
    event_args = {"track_index": 0, "device_index": 0, "parameter_index": 0, "parameter_value": "half"}
    result = validate_event_args(event_type, event_args)
    assert result.valid is False
    assert "Argument 'parameter_value' has type str, expected float" in result.errors


def test_validate_event_args_scene_added_valid():
    """
    Test validate_event_args for 'scene_added' with valid arguments.
    """
    event_type = "scene_added"
    event_args = {"scene_index": 0, "scene_name": "Intro"}
    result = validate_event_args(event_type, event_args)
    assert result.valid is True
    assert result.errors == []

def test_validate_event_args_scene_added_missing_required():
    """
    Test validate_event_args for 'scene_added' with missing required argument.
    """
    event_type = "scene_added"
    event_args = {"scene_name": "Intro"} # scene_index is missing
    result = validate_event_args(event_type, event_args)
    assert result.valid is False
    assert "Missing required arguments: scene_index" in result.errors

def test_validate_event_args_scene_removed_valid():
    """
    Test validate_event_args for 'scene_removed' with valid arguments.
    """
    event_type = "scene_removed"
    event_args = {"scene_index": 0}
    result = validate_event_args(event_type, event_args)
    assert result.valid is True
    assert result.errors == []

def test_validate_event_args_scene_reordered_valid():
    """
    Test validate_event_args for 'scene_reordered' with valid arguments.
    Note: A schema for 'scene_reordered' is not explicitly defined in schemas.py,
    so it should pass as an unknown event type. If a schema is added, this test
    will need to be updated.
    """
    event_type = "scene_reordered"
    event_args = {"old_index": 0, "new_index": 1}
    result = validate_event_args(event_type, event_args)
    assert result.valid is True
    assert result.errors == []


def test_validate_event_args_clip_slot_created_valid():
    """
    Test validate_event_args for 'clip_slot_created' with valid arguments.
    """
    event_type = "clip_slot_created"
    event_args = {"track_index": 0, "scene_index": 0, "has_clip": False}
    result = validate_event_args(event_type, event_args)
    assert result.valid is True
    assert result.errors == []

def test_validate_event_args_clip_slot_created_missing_required():
    """
    Test validate_event_args for 'clip_slot_created' with missing required argument.
    """
    event_type = "clip_slot_created"
    event_args = {"scene_index": 0} # track_index is missing
    result = validate_event_args(event_type, event_args)
    assert result.valid is False
    assert "Missing required arguments: track_index" in result.errors

def test_validate_event_args_clip_slot_changed_valid():
    """
    Test validate_event_args for 'clip_slot_changed' with valid arguments.
    """
    event_type = "clip_slot_changed"
    event_args = {"track_index": 0, "scene_index": 0, "playing_status": 1}
    result = validate_event_args(event_type, event_args)
    assert result.valid is True
    assert result.errors == []

def test_validate_event_args_clip_slot_changed_incorrect_type():
    """
    Test validate_event_args for 'clip_slot_changed' with incorrect type for an argument.
    """
    event_type = "clip_slot_changed"
    event_args = {"track_index": 0, "scene_index": 0, "playing_status": "playing"}
    result = validate_event_args(event_type, event_args)
    assert result.valid is False
    assert "Argument 'playing_status' has type str, expected int" in result.errors


def test_validate_event_args_tempo_changed_valid():
    """
    Test validate_event_args for 'tempo_changed' with valid arguments.
    """
    event_type = "tempo_changed"
    event_args = {"tempo": 120.5}
    result = validate_event_args(event_type, event_args)
    assert result.valid is True
    assert result.errors == []

def test_validate_event_args_tempo_changed_incorrect_type():
    """
    Test validate_event_args for 'tempo_changed' with incorrect type.
    """
    event_type = "tempo_changed"
    event_args = {"tempo": "fast"}
    result = validate_event_args(event_type, event_args)
    assert result.valid is False
    assert "Argument 'tempo' has type str, expected float" in result.errors

def test_validate_event_args_playback_state_changed_valid():
    """
    Test validate_event_args for 'playback_state_changed' with valid arguments.
    """
    event_type = "playback_state_changed"
    event_args = {"is_playing": True}
    result = validate_event_args(event_type, event_args)
    assert result.valid is True
    assert result.errors == []

def test_validate_event_args_playback_state_changed_incorrect_type():
    """
    Test validate_event_args for 'playback_state_changed' with incorrect type.
    """
    event_type = "playback_state_changed"
    event_args = {"is_playing": 1}
    result = validate_event_args(event_type, event_args)
    assert result.valid is False
    assert "Argument 'is_playing' has type int, expected bool" in result.errors




