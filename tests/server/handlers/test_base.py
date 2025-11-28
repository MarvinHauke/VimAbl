import pytest
from unittest.mock import patch
from src.server.handlers.base import EventResult, BaseEventHandler, broadcast_result

def test_event_result_ok_creates_success_result():
    """
    Test EventResult.ok() creates a successful result with optional diff and metadata.
    """
    diff_data = {"changes": ["node_added"]}
    metadata = {"source": "test"}
    result = EventResult.ok(diff=diff_data, **metadata)

    assert result.success is True
    assert result.diff == diff_data
    assert result.error_message is None
    assert result.error_type is None
    assert result.metadata == metadata

def test_event_result_ok_no_diff_no_metadata():
    """
    Test EventResult.ok() creates a successful result without diff or metadata.
    """
    result = EventResult.ok()

    assert result.success is True
    assert result.diff is None
    assert result.error_message is None
    assert result.error_type is None
    assert result.metadata == {}

def test_event_result_error_creates_error_result():
    """
    Test EventResult.error() creates an error result with message and type.
    """
    error_msg = "Something went wrong."
    error_type = "test_error"
    metadata = {"context": "failure"}
    result = EventResult.error(error_msg, error_type=error_type, **metadata)

    assert result.success is False
    assert result.diff is None
    assert result.error_message == error_msg
    assert result.error_type == error_type
    assert result.metadata == metadata

def test_event_result_error_default_type():
    """
    Test EventResult.error() uses default error_type if not provided.
    """
    error_msg = "Another error."
    result = EventResult.error(error_msg)

    assert result.success is False
    assert result.error_message == error_msg
    assert result.error_type == "handler_error"

def test_event_result_builder_pattern_with_diff():
    """
    Test EventResult builder pattern to add diff.
    """
    initial_result = EventResult(success=True)
    diff_data = {"type": "modified", "id": "123"}
    result = initial_result.with_diff(diff_data)

    assert result.diff == diff_data
    assert result.success is True # Ensure other properties are unchanged

def test_event_result_builder_pattern_with_metadata():
    """
    Test EventResult builder pattern to add metadata.
    """
    initial_result = EventResult(success=False, error_message="oops")
    metadata = {"timestamp": 12345}
    result = initial_result.with_metadata(**metadata)

    assert result.metadata == metadata
    assert result.success is False # Ensure other properties are unchanged
    assert result.error_message == "oops"

def test_event_result_bool_conversion():
    """
    Test boolean conversion of EventResult.
    """
    success_result = EventResult.ok()
    error_result = EventResult.error("Failed")

    assert bool(success_result) is True
    assert bool(error_result) is False

def test_event_result_str_representation():
    """
    Test string representation of EventResult.
    """
    success_result = EventResult.ok()
    error_result = EventResult.error("Failed processing.")

    assert "EventResult(success=True" in str(success_result)
    assert "error_message='Failed processing.'" in str(error_result)


class MockWebSocketServer:
    def __init__(self):
        self.broadcast_diff_called_with = None
        self.broadcast_error_called_with = None

    async def broadcast_diff(self, diff):
        self.broadcast_diff_called_with = diff

    async def broadcast_error(self, error_type, message):
        self.broadcast_error_called_with = (error_type, message)

    def is_running(self):
        return True

class MockServer:
    def __init__(self):
        self.websocket_server = MockWebSocketServer()
        self.current_ast = None # Not used for these tests, but required by BaseEventHandler

class MockEventHandler(BaseEventHandler):
    def __init__(self, server):
        super().__init__(server)

    @broadcast_result
    async def successful_handler(self, event_args):
        return EventResult.ok(diff={"key": "value"}, status="success")

    @broadcast_result
    async def successful_handler_no_diff(self, event_args):
        return EventResult.ok(status="success")

    @broadcast_result
    async def error_handler(self, event_args):
        return EventResult.error("Test error", error_type="test_error")

    @broadcast_result
    async def non_event_result_handler(self, event_args):
        return {"data": "some_data"} # Not an EventResult

@pytest.mark.asyncio
async def test_broadcast_result_successful_with_diff():
    """
    Test broadcast_result decorator with a successful EventResult that has a diff.
    """
    mock_server = MockServer()
    handler = MockEventHandler(mock_server)
    
    await handler.successful_handler({})

    assert mock_server.websocket_server.broadcast_diff_called_with == {"key": "value"}
    assert mock_server.websocket_server.broadcast_error_called_with is None

@pytest.mark.asyncio
async def test_broadcast_result_successful_no_diff():
    """
    Test broadcast_result decorator with a successful EventResult that has no diff.
    """
    mock_server = MockServer()
    handler = MockEventHandler(mock_server)
    
    await handler.successful_handler_no_diff({})

    assert mock_server.websocket_server.broadcast_diff_called_with is None
    assert mock_server.websocket_server.broadcast_error_called_with is None

@pytest.mark.asyncio
async def test_broadcast_result_error():
    """
    Test broadcast_result decorator with an EventResult indicating an error.
    """
    mock_server = MockServer()
    handler = MockEventHandler(mock_server)
    
    await handler.error_handler({})

    assert mock_server.websocket_server.broadcast_diff_called_with is None
    assert mock_server.websocket_server.broadcast_error_called_with == ("test_error", "Test error")

@pytest.mark.asyncio
async def test_broadcast_result_non_event_result():
    """
    Test broadcast_result decorator with a handler that does not return an EventResult.
    No broadcasting should occur.
    """
    mock_server = MockServer()
    handler = MockEventHandler(mock_server)
    
    await handler.non_event_result_handler({})

    assert mock_server.websocket_server.broadcast_diff_called_with is None
    assert mock_server.websocket_server.broadcast_error_called_with is None


from src.server.handlers.base import handle_exceptions # Import the decorator
import logging

class MockLogger:
    def __init__(self):
        self.exception_called = False
        self.exception_message = None

    def exception(self, message, exc_info=True):
        self.exception_called = True
        self.exception_message = message
        self.error = self.exception # Alias error to exception for testing purposes if needed

@pytest.fixture
def mock_logger(monkeypatch):
    mock = MockLogger()
    # Patch the logger instance in src.server.handlers.base
    with patch("src.server.handlers.base.logger", mock):
        yield mock

@pytest.mark.asyncio
async def test_handle_exceptions_successful_execution(mock_logger):
    """
    Test @handle_exceptions decorator with successful execution.
    """
    @handle_exceptions
    async def successful_func():
        return "Success!"

    result = await successful_func()
    assert result == "Success!"
    assert mock_logger.exception_called is False

@pytest.mark.asyncio
async def test_handle_exceptions_exception_handling(mock_logger):
    """
    Test @handle_exceptions decorator with an exception being raised.
    """
    @handle_exceptions
    async def failing_func():
        raise ValueError("Test value error")

    result = await failing_func()
    assert isinstance(result, EventResult)
    assert result.success is False
    assert "Test value error" in result.error_message
    assert result.error_type == "exception"
    assert result.metadata["exception_type"] == "ValueError"
    assert mock_logger.exception_called is True
    assert "Exception in failing_func" in mock_logger.exception_message

@pytest.mark.asyncio
async def test_handle_exceptions_custom_exception(mock_logger):
    """
    Test @handle_exceptions decorator with a custom exception type.
    """
    class CustomError(Exception):
        pass

    @handle_exceptions
    async def custom_failing_func():
        raise CustomError("Custom error message")

    result = await custom_failing_func()
    assert isinstance(result, EventResult)
    assert result.success is False
    assert "Custom error message" in result.error_message
    assert result.error_type == "exception"
    assert result.metadata["exception_type"] == "CustomError"
    assert mock_logger.exception_called is True
    assert "Exception in custom_failing_func" in mock_logger.exception_message