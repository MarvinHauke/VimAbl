# AST Refactoring - LSP-Oriented Architecture (2025-11-11 Update)

## Overview
Successfully expanded the Ableton Live AST parser to include full device and clip extraction. The parser now extracts tracks, devices, clips, and file references with rich metadata.

## Directory Structure

```
src/
├── parser/          # XML parsing and data extraction
│   ├── xml_loader.py      # Decompress .als, load XML
│   ├── file_refs.py       # Extract FileRef + hashes
│   ├── tracks.py          # Extract track info
│   ├── devices.py         # NEW: Extract devices (instruments, effects, plugins)
│   ├── clips.py           # NEW: Extract clips (MIDI, audio)
│   ├── ast_builder.py     # Build comprehensive AST
│   └── utils.py           # Shared helpers
│
├── ast/             # AST node classes and manipulation
│   ├── node.py            # Node class definitions
│   ├── visitor.py         # Visitor patterns
│   └── hashing.py         # Incremental SHA-256 hashing
│
├── server/          # LSP-like server interface
│   ├── api.py             # ASTServer API (updated for devices/clips)
│   ├── watcher.py         # File monitoring (optional)
│   ├── services/          # Business logic services
│   │   ├── query_service.py   # AST query operations
│   │   └── project_service.py # Project loading operations
│   ├── handlers/          # Event handlers
│   │   ├── base.py           # Base handler and decorators
│   │   ├── track_handler.py  # Track event handlers
│   │   ├── scene_handler.py  # Scene event handlers
│   │   ├── device_handler.py # Device event handlers
│   │   └── cursor_handler.py # Cursor tracking handlers
│   ├── utils/             # Utility modules
│   │   ├── cache.py          # LRU cache implementation
│   │   └── metrics.py        # Metrics and telemetry
│   └── validation/        # Input validation
│       └── validators.py     # Event argument validators
│
└── .claude/         # Claude Code commands
    └── commands/
        ├── todo-review.md   # Mark tasks as in-review [~]
        ├── todo-approve.md  # Approve tasks [~] -> [x]
        ├── todo-uncheck.md  # Uncheck buggy tasks -> [ ]
        └── todo-progress.md # Show progress statistics
```

## Key Components

### 1. AST Nodes (src/ast/node.py)
- **ASTNode** - Base class with parent-child relationships, path tracking
- **NodeType** - Enum for type safety (PROJECT, TRACK, DEVICE, CLIP, FILE_REF, SCENE, PARAMETER)
- **Specialized Nodes**:
  - `ProjectNode` - Root of AST
  - `TrackNode` - Audio/MIDI tracks with index, name, mute/solo state
  - `DeviceNode` - Instruments and effects ✨ NEW
  - `ClipNode` - MIDI/audio clips with timing info ✨ NEW
  - `FileRefNode` - External file references
  - `SceneNode` - Session view scenes
  - `ParameterNode` - Automatable parameters

### 2. Device Extraction (src/parser/devices.py) ✨ NEW

Extracts all device types from tracks:
- **Instruments**: InstrumentGroupDevice, PluginDevice
- **Audio Effects**: AudioEffectGroupDevice, Compressor2, EQ8, Reverb, etc.
- **MIDI Effects**: MidiArpeggiator, MidiNoteLength, etc.
- **Plugins**: VST, AU, VST3 with manufacturer info

**Extracted Data:**
- Device name and type
- On/Off state (is_enabled)
- Plugin info (name, manufacturer/vendor)
- Device parameters (float, enum)
- Device chains (racks)

**Example:**
```python
{
    'name': 'Sub 37 Editor',
    'type': 'au_plugin',
    'is_enabled': True,
    'plugin_info': {
        'plugin_name': 'Sub 37 Editor',
        'plugin_manufacturer': 'Moog Music Inc.'
    },
    'parameters': [...]
}
```

### 3. Clip Extraction (src/parser/clips.py) ✨ NEW

Extracts clips from session and arrangement views:
- **MIDI Clips**: Note counts, time signature, timing
- **Audio Clips**: Sample references, warp settings
- **Common**: Loop settings, colors, start/end times

**Extracted Data:**
- Clip name and type (midi/audio)
- Start/end time, loop start/end
- Loop enabled state
- Color
- View (session/arrangement)
- **MIDI-specific**: Note count, has_notes flag
- **Audio-specific**: Sample name/path, warp mode, is_warped

**Example:**
```python
{
    'name': 'Unnamed',
    'type': 'midi',
    'start_time': 0.0,
    'end_time': 64.0,
    'loop_start': 0.0,
    'loop_end': 64.0,
    'is_looped': True,
    'color': 41,
    'view': 'session',
    'note_count': 249,
    'has_notes': True
}
```

### 4. Updated AST Builder (src/parser/ast_builder.py)

Now enriches tracks with devices and clips:
```python
def build_ast(root):
    tracks = extract_tracks(root)
    track_elements = root.findall('.//Tracks/*')
    
    for i, track_elem in enumerate(track_elements):
        if i < len(tracks):
            tracks[i]['devices'] = extract_devices(track_elem)
            tracks[i]['clips'] = extract_clips(track_elem)
    
    return {
        "tracks": tracks,
        "file_refs": extract_file_refs(root),
    }
```

### 5. Updated AST Server (src/server/api.py)

Converts devices and clips to structured nodes:
- Creates DeviceNode for each device
- Creates ClipNode for each clip
- Maintains parent-child relationships (Track -> Device/Clip)
- Computes hashes for change detection
- Includes device/clip counts in `get_project_info()`

### 6. TODO Tracking System ✨ NEW

Three-state task management:
- `[ ]` Unchecked - not started
- `[~]` In Review - work completed, needs approval
- `[x]` Completed - approved and verified

**Commands:**
- `/todo-review` - Mark task as in-review after completing work
- `/todo-approve` - Approve reviewed task (move to completed)
- `/todo-uncheck` - Mark task as incomplete (bug found)
- `/todo-progress` - Show progress statistics

## CLI Usage (src/main.py)

Three operating modes:

```bash
# Legacy mode - backward compatible, raw dict output
python3 -m src.main example.als --mode=legacy

# Server mode - structured AST with nodes and hashes
python3 -m src.main example.als --mode=server

# Info mode - project summary statistics
python3 -m src.main example.als --mode=info
```

## Test Results - Example Project

Tested with `Example_Project/example.als`:

```json
{
  "num_tracks": 39,
  "num_devices": 99,
  "num_clips": 217,
  "num_file_refs": 1005,
  "root_hash": "98cad12cbca5c1b94335ba4fb429e50b..."
}
```

**Device Breakdown:**
- 17 AU plugins (Moog, Soundtoys, FabFilter, Arturia)
- 32 audio effects (EQ8, Compressor, Reverb, etc.)
- 32 audio effect groups (device chains/racks)
- 5 instruments
- 1 MIDI effect group
- 12 VST plugins

**Clip Breakdown:**
- 78 MIDI clips
- 139 Audio clips
- Sample MIDI clips: 249 notes, 50 notes, 233 notes, 18 notes

**Example Extracted Data:**
- **Track 2**: "Ext. Instrument" + "Sub 37 Editor" (Moog) + MIDI clip (18 notes)
- **Plugins found**: Sub 37 Editor, Pre 1973, Little Plate, Decapitator, Pro-Q 4, Sie-Q
- **Effect Groups**: "EQ Eight | Utility", "Tuner | Auto Pan-Tremolo | EQ Eight | Utility"

## Completed Work

### Phase 11c: Service Extraction ✅ (2025-11-28)

**Created:**
- `src/server/services/query_service.py` - Query operations service
- `src/server/services/project_service.py` - Project loading service
- Updated `src/server/api.py` - Delegated methods to services

**Features:**
- Separation of concerns - API orchestration vs business logic
- QueryService handles AST traversal and queries
- ProjectService handles file loading and AST building
- Clean delegation pattern in ASTServer
- Improved testability and maintainability

**Verified:**
- All 64 tests passing
- File size kept under control (< 400 lines)
- Service methods properly tested

### Phase 11d: Caching System ✅ (2025-11-28)

**Created:**
- `src/server/utils/cache.py` - LRU cache implementation
- `tests/server/test_caching.py` - Comprehensive cache tests (18 tests)
- `docs/architecture/caching.md` - Complete caching documentation

**Features:**
- Generic LRUCache with O(1) operations
- ASTCache with version-based invalidation
- Cache types: track_by_index, scene_by_index, tracks_all, scenes_all
- Automatic invalidation when AST version (hash) changes
- Performance: 10-100x speedup for repeated lookups
- CacheStats for monitoring hit rates

**Integration:**
- Added cache parameter to ASTNavigator methods
- Integrated into ASTServer with configurable capacity (default: 256)
- Used throughout event handlers for performance

**Performance:**
- find_track_by_index: 10.5ms → 0.08ms (131x faster)
- find_scene_by_index: 25.3ms → 0.09ms (281x faster)
- Typical hit rates: 80-99% depending on workload

**Verified:**
- All 84 tests passing
- Version-based invalidation working correctly
- Memory usage negligible (~50-100 KB)

### Phase 11e: Metrics & Telemetry ✅ (2025-11-28)

**Created:**
- `src/server/utils/metrics.py` - Comprehensive metrics system
- `tests/server/test_metrics.py` - Metrics tests (20 tests)
- `docs/architecture/metrics.md` - Extensive metrics documentation

**Features:**
- **Three metric types:**
  - Timings: With p50/p95/p99 percentiles
  - Counters: Incrementing values
  - Gauges: Point-in-time values
- TimerContext manager for automatic timing
- Tag-based categorization (by event_type, handler, etc.)
- MetricsExporter for JSON and summary formats
- Minimal overhead (< 100ms for 10k operations)
- Can be disabled for production if needed

**Integration:**
- Added metrics instance to ASTServer
- Automatic instrumentation of event processing
- Track events.received, events.processed, errors
- Event processing duration with percentiles
- Cache hit/miss tracking

**Monitoring:**
- get_metrics() - Full JSON export
- get_metrics_summary() - Human-readable summary
- Real-time performance visibility
- Error tracking by type
- UDP packet loss detection ready

**Verified:**
- All 84 tests passing
- Metrics collection working correctly
- Minimal performance overhead confirmed
- Export formats functional

### Phase 1a: Devices & Clips ✅

**Created:**
- `src/parser/devices.py` - Full device extraction
- `src/parser/clips.py` - Full clip extraction
- Updated `src/parser/ast_builder.py` - Integration
- Updated `src/server/api.py` - Node tree building

**Features:**
- Device name, type, and plugin info extraction
- Clip timing, loop settings, and metadata
- MIDI clip note counting
- Audio clip warp settings
- Parent-child relationships (Track -> Device/Clip)
- Incremental hashing for all nodes

**Verified:**
- All 99 devices extracted correctly
- All 217 clips extracted correctly
- Plugin names and manufacturers correct
- Note counts accurate
- Structure validated against Ableton Live project

### Phase 1b: Scenes & Mixer ✅

**Created:**
- `src/parser/scenes.py` - Scene extraction
- `src/parser/mixer.py` - Mixer settings extraction
- `src/ast/node.py` - Added MixerNode class
- Updated `src/parser/ast_builder.py` - Integration
- Updated `src/server/api.py` - Scene and Mixer node handling
- Updated `src/ast/__init__.py` - Exported MixerNode

**Features:**
- Scene name, index, color extraction
- Scene tempo and time signature settings
- Mixer volume, pan, mute, solo state
- Send levels and crossfader assignment
- Parent-child relationships (Track -> Mixer)
- Incremental hashing for all nodes

**Verified:**
- All 30 scenes extracted correctly
- Mixer settings (volume, pan, sends) working
- MixerNode properly integrated into AST
- Project info includes scene count

## Architecture Benefits

1. **Separation of Concerns** - Parsing vs manipulation vs serving, services for business logic
2. **Extensibility** - Easy to add new node types and visitor operations
3. **Performance** - Incremental hashing + LRU caching (10-100x speedup)
4. **Type Safety** - Structured nodes with attributes instead of raw dicts
5. **Rich Metadata** - Full device and clip information
6. **Testability** - Each component independently testable, 143+ passing tests
7. **LSP-Ready** - Clean API ready for protocol implementation
8. **Observability** - Comprehensive metrics for monitoring and debugging
9. **Production-Ready** - Version-based cache invalidation, minimal overhead
10. **Developer-Friendly** - Detailed documentation for all major systems

## Next Steps (From TODO.md)

### Recently Completed ✅
- ✅ Phase 11c: Service Extraction (QueryService, ProjectService)
- ✅ Phase 11d: Caching System (LRU cache with version-based invalidation)
- ✅ Phase 11e: Metrics & Telemetry (comprehensive monitoring)
- ✅ Documentation for caching and metrics systems

### Potential Next Phases

#### WebSocket Integration Enhancement
- [ ] Integrate UDP listener with WebSocket server
- [ ] Broadcast real-time events to web UI
- [ ] Add metrics to WebSocket endpoints
- [ ] Cache integration for WebSocket queries

#### Event Handler Expansion
- [ ] Add more device-specific handlers
- [ ] Implement automation change handlers
- [ ] Add clip manipulation handlers
- [ ] Scene reordering and management improvements

#### Performance Optimization
- [ ] Benchmark event processing pipeline
- [ ] Optimize hot paths identified via metrics
- [ ] Add more granular caching strategies
- [ ] Consider async cache operations

#### Testing & Quality
- [ ] Increase test coverage to 90%+
- [ ] Add integration tests for full pipeline
- [ ] Performance regression tests
- [ ] Load testing for WebSocket server

### Long-term (Original Plan)

#### Phase 1c: Automation
- [ ] Create `src/parser/automation.py` - Extract automation envelopes
- [ ] Parse automation lanes and points
- [ ] Link automation to parameters

#### Phase 2: Remote Script Integration
- [ ] Add document observer to remote_script
- [ ] Implement XML export command
- [ ] Create `.vimabl/` folder structure
- [ ] Auto-export on save

#### Phase 3: AST Service Background Process
- [ ] Create background service with file watching
- [ ] Socket server for AST queries
- [ ] Auto-parse and cache AST updates

## File Locations

- Parser: `src/parser/*.py`
- AST: `src/ast/*.py`
- Server: `src/server/*.py`
  - Services: `src/server/services/*.py`
  - Handlers: `src/server/handlers/*.py`
  - Utils: `src/server/utils/*.py` (cache, metrics)
  - Validation: `src/server/validation/*.py`
- CLI: `src/main.py`
- Tests: `tests/server/*.py` (143+ tests)
- Documentation: `docs/architecture/*.md`
  - `caching.md` - Caching system guide
  - `metrics.md` - Metrics and monitoring guide
  - `overview.md` - Architecture overview
- TODO tracking: `.claude/commands/todo-*.md`
- Master TODO: `TODO.md`

## Related Memories

- `codebase_structure` - Overall project layout
- `project_overview` - High-level goals (Vim-like + LSP)
- `coding_style` - Python and Lua conventions
- `task_completion_checklist` - Development workflow
