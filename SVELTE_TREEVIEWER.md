# 🎧 Ableton Live AST Visualizer

> A real-time visual representation of an Ableton Live Set's internal structure (AST), powered by Python, WebSockets, and Svelte.

---

## 🧠 Concept Overview

The **Ableton AST Visualizer** is a bridge between the static `.als` project format, the dynamic Live API, and a modern, reactive web UI.  
It parses, tracks, and renders the internal structure of a Live Set (tracks, devices, clips, samples, automation) in real time — similar to a _Tree-sitter playground_, but for music production data.

---

## 🧩 Architecture

    ┌────────────────────────────────────────┐
    │           Ableton Live Set             │
    │  (.als XML / Live API + Remote Script) │
    └────────────────────────────────────────┘
                        │
                        ▼
          ┌──────────────────────────┐
          │  Python AST Layer         │
          │  - Parses XML → JSON AST  │
          │  - Watches Live changes   │
          │  - Computes SHAs / Diffs  │
          └──────────────────────────┘
                        │
            (WebSocket JSON stream)
                        │
                        ▼
       ┌────────────────────────────────┐
       │  Svelte Frontend (Local Web UI)│
       │  - Renders AST interactively   │
       │  - Highlights live updates     │
       │  - Displays diffs + file refs  │
       └────────────────────────────────┘

---

## ⚙️ Core Components

| Component                            | Description                                                                                                            |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------- |
| **Parser (`src/parser/`)**           | Reads and converts `.als` → XML → JSON-based AST. Includes optional hashing (SHA-1) of device/sample references.       |
| **Remote Script Bridge**             | Ableton Live API integration for real-time changes. Sends lightweight event updates (e.g. track rename, clip trigger). |
| **AST Server (`src/server/`)**       | Python `aiohttp` or `FastAPI` server with WebSocket endpoint (`/ws`) broadcasting AST updates.                         |
| **Web Client (`src/web/frontend/`)** | Built with **SvelteKit** + Tailwind. Visualizes tree structure, highlights changes, and updates live.                  |

---

## 🚀 Features

- 🧩 **AST Parsing** – Extracts tracks, devices, clips, parameters, and file references.
- 🔄 **Live Updates** – Real-time synchronization with Ableton via Remote Script.
- 🧠 **SHA Tracking** – Each file reference is hashed for diff detection.
- 🌲 **Tree Visualization** – Interactive, collapsible AST explorer (like Tree-sitter Playground).
- ⚡ **Reactive Frontend** – Svelte frontend renders updates instantly over WebSocket.
- 🧰 **Extensible Design** – Easily integrates with your DAW tools, visual dashboards, or LSP-like servers.

---

## 🧮 Data Model (Simplified)

```json
{
  "project": {
    "name": "example.als",
    "tracks": [
      {
        "name": "Drums",
        "devices": [
          {
            "name": "Drum Rack",
            "sha": "b7e4ac...",
            "samples": [
              {
                "path": "Samples/Kick.wav",
                "sha": "a82c13...",
                "type": "audio/wav"
              }
            ]
          }
        ]
      }
    ]
  }
}
```

---

💻 Example Flow

Ableton emits change → Remote Script sends JSON event.

AST Server updates internal tree, computes diffs (e.g., track name or sample SHA).

WebSocket broadcasts updated subtree.

Svelte UI highlights modified nodes (green for new, red for removed, yellow for changed).

🌈 Future Extensions

🎚️ Clip and automation visualization

🔍 Search and filter (by name, SHA, sample path)

🧩 Diff viewer between Set versions

💾 Persistent AST snapshots

🎛️ Integration with Max for Live visualizers

🧭 Development Setup
Backend

```
# Run AST server
cd src/server
python api.py
```

Frontend

```
# Run Svelte UI

cd src/web/frontend
npm run dev
```

Then open http://localhost:5173
.
