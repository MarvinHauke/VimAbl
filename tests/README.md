# VimAbl Tests

This directory contains integration tests for the VimAbl WebSocket and UDP listener functionality.

## Test Files

### `test_integration.py`
Tests the integration between UDP listener and WebSocket server.

**What it tests:**
- UDP events are received on port 9002
- Events are successfully forwarded to WebSocket clients
- WebSocket clients receive real-time event updates

**Usage:**
```bash
# Start the WebSocket server first
python -m src.main Example_Project/example.xml --mode=websocket --ws-port=8765 --no-signals

# In another terminal, run the test
python tests/test_integration.py
```

**Expected output:**
```
✅ Integration test PASSED! UDP events are being forwarded to WebSocket clients.
```

### `test_fallback.py`
Tests the fallback mechanism when UDP events are missed.

**What it tests:**
- Sequence number gap detection
- Error notifications when gaps exceed threshold (5+ events)
- Fallback to XML diff mechanism

**Usage:**
```bash
# Start the WebSocket server first
python -m src.main Example_Project/example.xml --mode=websocket --ws-port=8765 --no-signals

# In another terminal, run the test
python tests/test_fallback.py
```

**Expected output:**
```
✅ Fallback test PASSED! Gap detection triggered warning.
```

### `test_websocket.py`
Basic WebSocket connection and message test.

**What it tests:**
- WebSocket server connectivity
- Initial FULL_AST message delivery

**Usage:**
```bash
# Start the WebSocket server first
python -m src.main Example_Project/example.xml --mode=websocket --ws-port=8765 --no-signals

# In another terminal, run the test
python tests/test_websocket.py
```

## Running All Tests

```bash
# Start the server
python -m src.main Example_Project/example.xml --mode=websocket --ws-port=8765 --no-signals &

# Run tests
python tests/test_integration.py
python tests/test_fallback.py
python tests/test_websocket.py

# Stop the server
kill %1
```

## Dependencies

All tests require:
- `websockets` - for WebSocket client connections
- `asyncio` - for async operations
- Running WebSocket server on port 8765
- Available UDP port 9002

## Notes

- Tests are designed to run independently
- Each test connects to a running WebSocket server
- Tests send UDP messages directly to port 9002
- Server must be started before running tests
