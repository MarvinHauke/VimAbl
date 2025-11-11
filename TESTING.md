# Testing the VimAbl WebSocket TreeViewer

## Quick Test Methods

### Method 1: Python Test Script (Automated)

```bash
# From project root
uv run python test_websocket.py
```

**Expected Output:**
```
Connecting to ws://localhost:8765...
Connected!

Received message type: FULL_AST
AST root type: project
AST root hash: 6217847101d65d48...
Number of children: 1074
  Child 0: track -
  Child 1: track -
  Child 2: track -

Test successful!
```

✅ If you see this, the WebSocket server is working correctly!

---

### Method 2: Browser Test (Visual)

1. **Open the app:**
   - Navigate to http://localhost:5173 in your browser

2. **Check Connection Status:**
   - Look for the connection indicator at the top
   - Should show: `🟢 Connected`
   - If connecting: `🟡 Connecting...`
   - If error: `🔴 Error: [message]`

3. **Open Browser Console:**
   - **Chrome/Edge:** `Cmd+Option+J` (Mac) or `F12` (Windows/Linux)
   - **Firefox:** `Cmd+Option+K` (Mac) or `F12` (Windows/Linux)
   - **Safari:** `Cmd+Option+C` (Mac)

4. **Look for WebSocket logs:**
   ```
   [WebSocket] Connecting to ws://localhost:8765...
   [WebSocket] Connected
   [WebSocket] Received message: FULL_AST
   AST received: {node_type: "project", id: "project", ...}
   ```

5. **Verify AST Display:**
   - Should see "Project AST" section
   - Shows: Type, ID, Children count
   - Lists first 10 child nodes with details

---

### Method 3: Command Line WebSocket Test (wscat)

If you have `wscat` installed:

```bash
# Install wscat (if not installed)
npm install -g wscat

# Connect to WebSocket server
wscat -c ws://localhost:8765

# You should immediately receive the FULL_AST message
```

**Expected Response:**
```json
{
  "type": "FULL_AST",
  "payload": {
    "ast": {
      "node_type": "project",
      "id": "project",
      "hash": "6217847101...",
      "attributes": {},
      "children": [...]
    }
  }
}
```

---

### Method 4: Browser DevTools Network Tab

1. Open browser DevTools (`F12`)
2. Go to **Network** tab
3. Filter by **WS** (WebSocket)
4. Reload the page
5. Click on the WebSocket connection
6. Go to **Messages** sub-tab
7. See all WebSocket messages in real-time

---

### Method 5: cURL WebSocket Test

```bash
# Test basic connection
curl -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Key: $(echo -n "test" | base64)" \
  http://localhost:8765
```

---

## Troubleshooting

### Connection Refused Error

**Symptom:** `Error: WebSocket connection refused`

**Solution:**
```bash
# Check if WebSocket server is running
lsof -i :8765

# If not, start it:
uv run python -m src.main Example_Project/example.als --mode=websocket
```

### Port Already in Use

**Symptom:** `OSError: [Errno 48] address already in use`

**Solution:**
```bash
# Kill process on port 8765
lsof -ti :8765 | xargs kill -9

# Restart server
uv run python -m src.main Example_Project/example.als --mode=websocket
```

### No AST Data Displayed

**Symptom:** Shows "Waiting for AST data..."

**Checks:**
1. Is WebSocket server running? `lsof -i :8765`
2. Is connection status "Connected"?
3. Check browser console for errors
4. Try refreshing the page

### WebSocket Keeps Reconnecting

**Symptom:** Connection status flickers between "Connecting" and "Disconnected"

**Solution:**
- Check WebSocket server logs for errors
- Verify the server didn't crash
- Check firewall settings (if applicable)

---

## Expected Behavior

### On Page Load:
1. ✅ Connection status: "Connecting..."
2. ✅ Connection status changes to: "Connected" 🟢
3. ✅ AST data appears within 1-2 seconds
4. ✅ First 10 nodes are displayed

### WebSocket Messages:
- **On Connect:** Receive `FULL_AST` message
- **Message Size:** ~several MB for large projects
- **Children:** 1074 nodes (for Example_Project)

### Browser Console:
```
[WebSocket] Connecting to ws://localhost:8765...
[WebSocket] Connected
[WebSocket] Received message: FULL_AST
AST received: {node_type: "project", ...}
```

---

## Performance Expectations

| Metric | Expected Value |
|--------|---------------|
| Connection Time | < 500ms |
| First Message | < 1s |
| UI Update | < 100ms |
| Page Load | < 2s |

---

## Advanced Testing

### Test Reconnection:

1. Open app in browser (should connect)
2. Stop WebSocket server: `Ctrl+C`
3. Connection status should show: "Disconnected"
4. Restart server
5. App should auto-reconnect within 3-9 seconds (exponential backoff)

### Test Multiple Clients:

1. Open http://localhost:5173 in multiple browser tabs
2. All should connect successfully
3. Check server logs - should show multiple clients

### Test Large Project:

```bash
# Use a larger Ableton project
uv run python -m src.main /path/to/large/project.als --mode=websocket
```

Check:
- Connection time
- Message size
- UI responsiveness
- Memory usage

---

## What You Should See in Browser

### Header Section:
```
🎧 VimAbl AST TreeViewer
Real-time Ableton Live project visualization
🟢 Connected  Last update: 12:34:56 PM
```

### AST Display:
```
Project AST

Type: project
ID: project
Children: 1074

First 10 Nodes:

Type: track
ID: track_0
Name: (unnamed)

Type: track
ID: track_1
Name: (unnamed)

[... 8 more nodes ...]
```

---

## Logs to Monitor

### WebSocket Server Terminal:
```
Starting WebSocket server on ws://localhost:8765
Loading project: Example_Project/example.als
Project loaded: 62178471...

Project Info:
  Tracks: 39
  Devices: 99
  Clips: 217
  Scenes: 30
  File References: 1005

WebSocket Server:
  Running: True
  URL: ws://localhost:8765
  Connected clients: 0

Server is running. Press Ctrl+C to stop.
```

### Svelte Dev Server Terminal:
```
VITE v7.2.2  ready in 732 ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
```

---

## Success Criteria

✅ **All Tests Pass When:**
1. Python test script shows "Test successful!"
2. Browser shows "Connected" status
3. AST data is displayed on page
4. Browser console shows WebSocket messages
5. No errors in either terminal

🎉 **If all checks pass, Phase 2 is complete!**
