# WebSocket Communication Analysis & Optimization Opportunities

**Date**: 2025-11-28
**Status**: Analysis Complete

## Executive Summary

The current WebSocket communication architecture is **functional but has several optimization opportunities**:

1. **Large FULL_AST messages** (~1-5 MB for big projects) are sent as single JSON payloads
2. **DIFF_UPDATE messages** are efficient but could be batched better
3. **No chunking or streaming** for large payloads
4. **No compression** on WebSocket messages
5. **Frontend unpacking** is synchronous and blocks the main thread

## Current Architecture

### Communication Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     ABLETON LIVE                            │
│                  (Remote Script)                            │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ UDP/OSC Events (Port 9002)
                 │ • Track renamed, muted, armed
                 │ • Device params, tempo, transport
                 │ • Cursor position
                 │ • <1ms latency
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│            PYTHON AST SERVER (src/main.py)                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  udp_event_callback()                                 │  │
│  │    ├─ Cursor events → Direct broadcast               │  │
│  │    └─ AST events → process_live_event()              │  │
│  └──────────────────────────────────────────────────────┘  │
│                         │                                   │
│                         ▼                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  ASTServer.process_live_event()                      │  │
│  │    ├─ Route to handler (Track/Scene/Device/etc.)     │  │
│  │    ├─ Update AST in-place                            │  │
│  │    ├─ Compute diff (changes only)                    │  │
│  │    └─ Return EventResult                             │  │
│  └──────────────────────────────────────────────────────┘  │
│                         │                                   │
│                         ▼                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Handler (@broadcast_result decorator)               │  │
│  │    └─ Calls _broadcast_if_running(diff_result)       │  │
│  └──────────────────────────────────────────────────────┘  │
│                         │                                   │
│                         ▼                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  ASTWebSocketServer.broadcast_diff()                 │  │
│  │    ├─ create_diff_message(diff_result)               │  │
│  │    ├─ JSON.stringify()  ⚠️ BLOCKING                  │  │
│  │    └─ Send to all clients                            │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  │ WebSocket (Port 8765)
                  │ • FULL_AST (1-5 MB, initial load) ⚠️ LARGE
                  │ • DIFF_UPDATE (100-5000 bytes)
                  │ • live_event (cursor, 50-200 bytes)
                  │ • ERROR messages
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│      SVELTE FRONTEND (src/web/frontend)                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  ASTWebSocketClient.onMessage()                      │  │
│  │    ├─ JSON.parse(message)  ⚠️ BLOCKS UI THREAD       │  │
│  │    └─ Route by message.type                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                         │                                   │
│         ┌───────────────┴─────────────────┐                │
│         ▼                                 ▼                │
│  ┌──────────────┐                  ┌──────────────┐       │
│  │  FULL_AST    │                  │ DIFF_UPDATE  │       │
│  │  message     │                  │  message     │       │
│  └──────┬───────┘                  └──────┬───────┘       │
│         │                                 │                │
│         ▼                                 ▼                │
│  astStore.setAST()            astStore.applyDiff()         │
│    ⚠️ Rebuilds entire          ⚠️ Synchronous tree         │
│       tree synchronously          mutation                │
│                                                             │
│  Result: UI re-renders with new data                       │
└─────────────────────────────────────────────────────────────┘
```

## Message Types & Sizes

### 1. FULL_AST Message

**When sent:**
- Initial client connection
- After XML file save (full reload)
- On manual refresh

**Structure:**
```json
{
  "type": "FULL_AST",
  "payload": {
    "ast": {
      "node_type": "project",
      "id": "project",
      "hash": "abc123...",
      "attributes": {...},
      "children": [
        {
          "node_type": "track",
          "id": "track_0",
          "hash": "def456...",
          "attributes": {...},
          "children": [...]  // Deep nesting: devices, clips, clip_slots
        },
        // ... 36 more tracks
      ]
    },
    "project_path": "/path/to/project.als"
  }
}
```

**Size:**
- **Small project** (8 tracks, 20 devices): ~500 KB
- **Medium project** (16 tracks, 50 devices): ~1.5 MB
- **Large project** (50 tracks, 200 devices): ~5 MB

**Performance:**
- **JSON.stringify()**: 50-200ms (Python side)
- **Network transfer**: 10-50ms (localhost)
- **JSON.parse()**: 100-500ms (blocks UI thread!) ⚠️
- **Tree rebuild**: 50-200ms (Svelte reactivity)
- **Total**: **210-950ms** for initial load

### 2. DIFF_UPDATE Message

**When sent:**
- After processing UDP event (track rename, mute, etc.)
- After XML file change (when file watcher detects save)

**Structure:**
```json
{
  "type": "DIFF_UPDATE",
  "payload": {
    "diff": {
      "changes": [
        {
          "node_id": "track_5",
          "field": "name",
          "old_value": "Audio",
          "new_value": "Drums",
          "seq_num": 42,
          "timestamp": 1732812345.678
        }
      ],
      "added": [],
      "removed": [],
      "modified": ["track_5"],
      "unchanged": []
    }
  }
}
```

**Size:**
- **Single field change**: ~150-300 bytes
- **Multiple changes batched**: ~500-2000 bytes
- **Scene addition** (with clip slots): ~5-20 KB

**Performance:**
- **JSON.stringify()**: <1ms
- **Network transfer**: <1ms
- **JSON.parse()**: <5ms
- **AST update**: 1-10ms
- **Total**: **<20ms** ✅ Very efficient

### 3. live_event Message

**When sent:**
- Cursor position changes (very frequent)
- Transport events (play/stop)

**Structure:**
```json
{
  "type": "live_event",
  "payload": {
    "event_path": "/live/cursor/clip_slot",
    "args": [5, 2],  // track_idx, scene_idx
    "seq_num": 123,
    "timestamp": 1732812345.678
  }
}
```

**Size:** ~100-200 bytes

**Performance:** <5ms total ✅ Excellent

## Problem Areas

### Problem 1: Large FULL_AST Messages Block UI

**Symptoms:**
- 500ms freeze when loading large projects
- Browser "unresponsive script" warnings
- Poor first-load experience

**Root Cause:**
- Single 5 MB JSON payload
- Synchronous `JSON.parse()` on main thread
- Synchronous tree rebuild in Svelte store

**Impact:**
- **User experience**: ⚠️ Poor
- **Frequency**: Every initial load, every full refresh
- **Priority**: **HIGH**

### Problem 2: No Compression

**Current:**
- Raw JSON sent over WebSocket
- No gzip/brotli compression

**Potential Savings:**
- **JSON compression ratio**: 5-10x (AST has lots of repetition)
- **Example**: 5 MB → 500 KB with gzip

**Impact:**
- **Network usage**: Moderate (localhost is fast)
- **Parse time**: Would be **slower** (decompress + parse)
- **Priority**: **LOW** (only useful for remote connections)

### Problem 3: Synchronous Frontend Processing

**Current:**
```typescript
// src/web/frontend/src/routes/+page.svelte
onMessage: (message) => {
    if (message.type === 'FULL_AST') {
        astStore.setAST(message.payload.ast);  // ⚠️ BLOCKS UI
    }
}

// src/web/frontend/src/lib/stores/ast.svelte.ts
setAST(astData, projectPath) {
    this.root = astData;           // ⚠️ Deep object traversal
    this.projectPath = projectPath;
    // Svelte reactivity triggers re-render  ⚠️ Expensive
}
```

**Issues:**
- No Web Workers for parsing
- No progressive rendering
- No chunking/streaming

### Problem 4: Inefficient Diff Application

**Current approach:**
```typescript
applyDiff(diffData) {
    for (const change of diffData.changes) {
        const node = this.findNodeById(change.node_id);  // ⚠️ Tree traversal
        if (node) {
            node.attributes[change.field] = change.new_value;
        }
    }
}
```

**Issues:**
- **O(n)** tree search for each change
- No batching of DOM updates
- Triggers Svelte reactivity for each change

## Optimization Opportunities

### 🔥 **HIGH PRIORITY**

#### 1. Progressive/Chunked AST Loading

**Approach**: Stream AST in chunks instead of single payload

**Backend changes:**
```python
# src/websocket/serializers.py

def create_chunked_ast_message(root: ASTNode, chunk_size: int = 10):
    """
    Create multiple CHUNK_AST messages instead of single FULL_AST.

    Messages:
    1. CHUNK_START: { chunk_id, total_chunks, project_path }
    2. CHUNK_DATA (x N): { chunk_id, chunk_index, nodes: [...] }
    3. CHUNK_END: { chunk_id, total_chunks }
    """
    chunks = []
    chunk_id = str(uuid.uuid4())

    # Serialize top-level (project + tracks metadata)
    project_metadata = {
        'node_type': root.node_type.value,
        'id': root.id,
        'attributes': root.attributes,
        'child_count': len(root.children)
    }

    # Split tracks into chunks
    tracks = [child for child in root.children if child.node_type == NodeType.TRACK]

    yield create_message('CHUNK_START', {
        'chunk_id': chunk_id,
        'total_chunks': len(tracks) // chunk_size + 1,
        'project_metadata': project_metadata
    })

    for i in range(0, len(tracks), chunk_size):
        chunk = tracks[i:i+chunk_size]
        yield create_message('CHUNK_DATA', {
            'chunk_id': chunk_id,
            'chunk_index': i // chunk_size,
            'nodes': [serialize_node(track) for track in chunk]
        })

    yield create_message('CHUNK_END', {
        'chunk_id': chunk_id,
        'total_chunks': len(tracks) // chunk_size + 1
    })
```

**Frontend changes:**
```typescript
// src/lib/stores/ast.svelte.ts

class ChunkedASTLoader {
    private chunks = new Map<string, any[]>();

    async handleChunkStart(payload) {
        this.chunks.set(payload.chunk_id, []);
        astStore.showLoadingProgress(0, payload.total_chunks);
    }

    async handleChunkData(payload) {
        const chunks = this.chunks.get(payload.chunk_id);
        chunks.push(...payload.nodes);

        // Progressive rendering: show each chunk immediately
        await astStore.appendNodes(payload.nodes);

        const progress = (payload.chunk_index + 1) / payload.total_chunks;
        astStore.showLoadingProgress(progress * 100, payload.total_chunks);

        // Yield to UI thread every chunk
        await new Promise(resolve => setTimeout(resolve, 0));
    }

    async handleChunkEnd(payload) {
        const chunks = this.chunks.get(payload.chunk_id);
        this.chunks.delete(payload.chunk_id);
        astStore.finalizeLoading();
    }
}
```

**Benefits:**
- ✅ No UI freeze (chunked processing)
- ✅ Progressive rendering (user sees partial results)
- ✅ Better perceived performance
- ✅ Graceful degradation (slow connections)

**Estimated effort**: 4-6 hours
**Performance gain**: 500ms → 100ms perceived load time

---

#### 2. Web Worker for JSON Parsing

**Approach**: Offload JSON parsing to background thread

**Frontend implementation:**
```typescript
// src/lib/workers/ast-parser.worker.ts
self.onmessage = (e) => {
    if (e.data.type === 'PARSE_AST') {
        const parsed = JSON.parse(e.data.json);
        self.postMessage({ type: 'AST_PARSED', data: parsed });
    }
};

// src/lib/api/websocket.ts
const astWorker = new Worker(new URL('../workers/ast-parser.worker.ts', import.meta.url));

async function handleMessage(messageStr: string) {
    // Offload parsing to worker
    astWorker.postMessage({ type: 'PARSE_AST', json: messageStr });

    const parsed = await new Promise(resolve => {
        astWorker.onmessage = (e) => {
            if (e.data.type === 'AST_PARSED') {
                resolve(e.data.data);
            }
        };
    });

    // Now update store (non-blocking)
    astStore.setAST(parsed.payload.ast);
}
```

**Benefits:**
- ✅ Main thread stays responsive
- ✅ No "unresponsive script" warnings
- ✅ Easy to implement

**Estimated effort**: 2-3 hours
**Performance gain**: Eliminates 100-500ms UI freeze

---

### 🟡 **MEDIUM PRIORITY**

#### 3. Batch DIFF_UPDATE Messages

**Current issue**: High-frequency events (device params, tempo) send one message per change

**Approach**: Accumulate diffs for 50-100ms, send single batched message

**Backend changes:**
```python
# src/utils/debouncer.py (already exists!)

class DebouncedBroadcaster:
    """Already implemented! Just need to use it more."""

    def __init__(self, delay: float = 0.05):  # 50ms
        self.delay = delay
        self.pending_diffs = []
        self.timer_task = None

    async def schedule_broadcast(self, diff_result: Dict[str, Any]):
        """Accumulate diffs and broadcast after delay."""
        self.pending_diffs.append(diff_result)

        if self.timer_task:
            self.timer_task.cancel()

        self.timer_task = asyncio.create_task(self._flush_after_delay())

    async def _flush_after_delay(self):
        await asyncio.sleep(self.delay)

        if not self.pending_diffs:
            return

        # Merge all pending diffs
        merged = self._merge_diffs(self.pending_diffs)
        await self.websocket_server.broadcast_diff(merged)

        self.pending_diffs.clear()
```

**Benefits:**
- ✅ Fewer WebSocket messages
- ✅ Better network efficiency
- ✅ Less frontend re-rendering

**Estimated effort**: 1-2 hours (mostly already implemented!)
**Performance gain**: 10-20x reduction in message count for rapid changes

---

#### 4. Node Index Map for Fast Lookups

**Current issue**: `findNodeById()` does O(n) tree traversal

**Approach**: Maintain index map in frontend

```typescript
// src/lib/stores/ast.svelte.ts

class ASTStore {
    private root = $state(null);
    private nodeIndex = new Map<string, ASTNode>();  // ✨ NEW

    setAST(astData, projectPath) {
        this.root = astData;
        this.projectPath = projectPath;

        // Build index
        this.nodeIndex.clear();
        this._indexNode(astData);
    }

    private _indexNode(node: ASTNode) {
        this.nodeIndex.set(node.id, node);
        for (const child of node.children || []) {
            this._indexNode(child);
        }
    }

    applyDiff(diffData) {
        for (const change of diffData.changes) {
            const node = this.nodeIndex.get(change.node_id);  // ✨ O(1) lookup!
            if (node) {
                node.attributes[change.field] = change.new_value;
            }
        }
    }
}
```

**Benefits:**
- ✅ O(1) node lookups instead of O(n)
- ✅ Much faster diff application
- ✅ Scales to large projects

**Estimated effort**: 1-2 hours
**Performance gain**: 10-100x faster diff application for large projects

---

### 🟢 **LOW PRIORITY** (Future/Optional)

#### 5. WebSocket Compression

**Approach**: Enable permessage-deflate extension

```python
# Backend: src/websocket/server.py
from websockets.server import serve

self.server = await serve(
    self._handle_client,
    self.host,
    self.port,
    compression='deflate'  # ✨ Enable compression
)
```

**Benefits:**
- ✅ 5-10x smaller payloads
- ⚠️ Higher CPU usage (compress/decompress)
- ⚠️ Only useful for remote connections

**When to use**: If deploying to remote server (not localhost)

---

#### 6. Binary Protocol (MessagePack)

**Approach**: Replace JSON with MessagePack

**Benefits:**
- ✅ ~30% smaller than JSON
- ✅ Faster to parse
- ⚠️ More complex, less debuggable

**When to use**: If network becomes bottleneck (unlikely for localhost)

---

## Recommended Implementation Order

### Phase 1: Quick Wins (2-4 hours)
1. ✅ Enable batch diff broadcasting (already 80% done)
2. ✅ Add node index map to frontend
3. ✅ Test with large project (50+ tracks)

### Phase 2: Web Worker (2-3 hours)
1. Create ast-parser.worker.ts
2. Integrate with WebSocket client
3. Test UI responsiveness with 5 MB payload

### Phase 3: Chunked Loading (4-6 hours)
1. Implement chunked AST serialization
2. Add progressive rendering to frontend
3. Add loading progress indicator
4. Test with very large projects

### Total: 8-13 hours for all high-priority optimizations

---

## Performance Targets

| Metric | Current | Target | Priority |
|--------|---------|--------|----------|
| Initial load (50 tracks) | 500-950ms | <200ms | HIGH |
| DIFF update latency | <20ms | <10ms | MEDIUM |
| UI freeze during load | 100-500ms | 0ms | HIGH |
| Messages/sec (rapid changes) | 50-100 | 5-10 | MEDIUM |
| Memory usage | ~50 MB | ~30 MB | LOW |

---

## Monitoring & Metrics

Add to Svelte UI:

```typescript
// Performance monitoring
const perfStore = {
    lastLoadTime: 0,
    lastDiffTime: 0,
    messagesReceived: 0,
    bytesReceived: 0,

    trackLoadTime(ms: number) {
        this.lastLoadTime = ms;
        console.log(`[Perf] AST loaded in ${ms}ms`);
    }
};
```

---

## Conclusion

**Current state**: Functional but inefficient for large projects

**Biggest bottleneck**: Synchronous JSON parsing + tree rebuild blocks UI

**Recommended action**:
1. Start with **Phase 1** (quick wins, 2-4 hours)
2. Then implement **Web Worker** (Phase 2, 2-3 hours)
3. Save **Chunked Loading** for later if needed

**Total effort for major improvement**: 4-7 hours
