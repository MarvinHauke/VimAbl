# AST Refactoring - LSP-Oriented Architecture (2025-11-10)

## Overview
Successfully refactored the Ableton Live AST parser from a simple dict-based parser to a full LSP-oriented architecture with structured node classes, visitor patterns, and server API.

## New Directory Structure

```
src/
├── parser/          # XML parsing and data extraction
│   ├── xml_loader.py      # Decompress .als, load XML
│   ├── file_refs.py       # Extract FileRef + hashes
│   ├── tracks.py          # Extract track info
│   ├── ast_builder.py     # Build raw dict AST
│   └── utils.py           # Shared helpers
│
├── ast/             # AST node classes and manipulation
│   ├── node.py            # Node class definitions
│   ├── visitor.py         # Visitor patterns
│   └── hashing.py         # Incremental SHA-256 hashing
│
└── server/          # LSP-like server interface
    ├── api.py             # ASTServer API
    └── watcher.py         # File monitoring (optional)
```

## Key Components

### 1. AST Nodes (src/ast/node.py)
- **ASTNode** - Base class with parent-child relationships, path tracking
- **NodeType** - Enum for type safety (PROJECT, TRACK, DEVICE, CLIP, FILE_REF, SCENE, PARAMETER)
- **Specialized Nodes**:
  - `ProjectNode` - Root of AST
  - `TrackNode` - Audio/MIDI tracks with index, name, mute/solo state
  - `DeviceNode` - Instruments and effects
  - `ClipNode` - MIDI/audio clips with timing info
  - `FileRefNode` - External file references
  - `SceneNode` - Session view scenes
  - `ParameterNode` - Automatable parameters

### 2. Visitor Patterns (src/ast/visitor.py)
- **ASTVisitor** - Base visitor with double dispatch pattern
- **SerializationVisitor** - Convert AST to JSON with optional hash inclusion
- **DiffVisitor** - Compare two ASTs, find added/removed/modified nodes
- **PrettyPrintVisitor** - Human-readable indented output
- **SearchVisitor** - Query by ID, type, or predicate function

### 3. Hashing System (src/ast/hashing.py)
- **NodeHasher** - Computes SHA-256 for nodes
- **Incremental hashing** - Parent hash includes only child hashes, not full content
- **Fast change detection** - Compare hashes instead of full tree traversal
- **`hash_tree()`** - Convenience function to hash entire tree
- **`find_modified_nodes()`** - Efficiently find changes between versions

### 4. AST Server (src/server/api.py)
High-level API for LSP features:
- `load_project(path)` - Load .als file, build AST, compute hashes
- `get_ast_json(include_hash)` - Serialize full AST to JSON
- `find_node_by_id(id)` - Query specific node
- `find_nodes_by_type(type)` - Find all nodes of a type
- `diff_with_file(other_path)` - Compare with another project
- `get_project_info()` - Get statistics (track count, file refs, etc.)
- `query_nodes(predicate)` - Simple predicate-based search

### 5. File Watcher (src/server/watcher.py)
Optional component (requires `watchdog` package):
- **FileWatcher** - Monitor .als/.xml files for changes
- **Debouncing** - Avoid duplicate events (1 second window)
- **Context manager support** - `with FileWatcher(...) as watcher:`
- **Callback-based** - Execute custom function on file change

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

## Migration from Old Structure

**Before:**
```
src/ast/
├── xml_loader.py
├── file_refs.py
├── tracks.py
├── ast_builder.py
└── utils.py
```

**After:**
```
src/parser/        # Moved parsing logic here
src/ast/           # NEW: Node manipulation
src/server/        # NEW: LSP interface
```

## Import Changes

Old:
```python
from src.ast.xml_loader import load_ableton_xml
from src.ast.ast_builder import build_ast
```

New:
```python
from src.parser import load_ableton_xml, build_ast
from src.server import ASTServer
from src.ast import TrackNode, SearchVisitor, hash_tree
```

## Code Examples

### Load and Query Project
```python
from src.server import ASTServer
from src.ast import SearchVisitor, NodeType
from pathlib import Path

# Load project
server = ASTServer()
server.load_project(Path('example.als'))

# Get info
info = server.get_project_info()
# {'num_tracks': 39, 'num_file_refs': 1005, ...}

# Search for tracks
search = SearchVisitor()
tracks = search.find_by_type(server.current_ast, NodeType.TRACK)

# Find specific node
track_0 = search.find_by_id(server.current_ast, 'track_0')
```

### Diff Two Projects
```python
server = ASTServer()
server.load_project(Path('version1.als'))
changes = server.diff_with_file(Path('version2.als'))
# Returns list of added/removed/modified nodes
```

### Watch for Changes
```python
from src.server import FileWatcher

def on_change(file_path):
    server.load_project(file_path)
    print(f"Reloaded: {server.get_project_info()}")

watcher = FileWatcher(on_change)
watcher.watch(Path('example.als'))
watcher.start()
```

## Testing Results

All functionality tested and working:
- ✅ Legacy mode maintains exact backward compatibility
- ✅ Server mode produces structured AST with hashes
- ✅ Info mode shows correct statistics
- ✅ Visitor patterns work correctly
- ✅ Search by ID/type operational
- ✅ Node relationships (parent/child) correct

**Test project stats:**
- 39 tracks found
- 1005 file references extracted
- Root hash computed: `bfc8f68fcf91ec1979efe9728b110758...`

## Dependencies

Added `requirements.txt`:
```
watchdog>=3.0.0  # Optional, for file watching
```

FileWatcher import is wrapped in try/except, so it's truly optional.

## Architecture Benefits

1. **Separation of Concerns** - Parsing vs manipulation vs serving
2. **Extensibility** - Easy to add new node types and visitor operations
3. **Performance** - Incremental hashing enables fast diff/caching
4. **Type Safety** - Structured nodes with attributes instead of raw dicts
5. **Testability** - Each component independently testable
6. **LSP-Ready** - Clean API ready for protocol implementation

## Next Steps for LSP Implementation

1. **Expand parser** - Extract devices, clips, automation
2. **LSP protocol handlers** - Implement textDocument/*, workspace/* methods
3. **Rename/refactor operations** - Modify AST and write back to XML
4. **Hover/completion** - Use AST queries for editor features
5. **Transport layer** - Add stdio/socket communication
6. **Caching** - Use hashes to avoid reparsing unchanged files
7. **Custom methods** - Add ableton/* protocol extensions

## File Locations

- Parser: `src/parser/*.py`
- AST: `src/ast/*.py` 
- Server: `src/server/*.py`
- CLI: `src/main.py`
- Tests: Verified via CLI modes
- Docs: `REFACTORING_SUMMARY.md`

## Related Memories

- `codebase_structure` - Overall project layout
- `project_overview` - High-level goals (Vim-like + LSP)
