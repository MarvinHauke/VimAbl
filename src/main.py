import asyncio
import json
import sys
import signal
from pathlib import Path

from src.parser import load_ableton_xml, build_ast
from src.server import ASTServer


async def run_websocket_server(path: Path, host: str, port: int, use_signals: bool = True):
    """Run the WebSocket server with file watching."""
    print(f"Starting WebSocket server on ws://{host}:{port}")
    print(f"Loading project: {path}")

    # Create server with WebSocket enabled
    server = ASTServer(enable_websocket=True, ws_host=host, ws_port=port)

    # Start WebSocket server
    await server.start_websocket_server()

    # Load the project
    result = server.load_project(path)
    print(f"Project loaded: {result['root_hash'][:8]}...")

    # Show project info
    info = server.get_project_info()
    print(f"\nProject Info:")
    print(f"  Tracks: {info['num_tracks']}")
    print(f"  Devices: {info['num_devices']}")
    print(f"  Clips: {info['num_clips']}")
    print(f"  Scenes: {info['num_scenes']}")
    print(f"  File References: {info['num_file_refs']}")

    # Show WebSocket status
    ws_status = server.get_websocket_status()
    print(f"\nWebSocket Server:")
    print(f"  Running: {ws_status['running']}")
    print(f"  URL: ws://{ws_status['host']}:{ws_status['port']}")
    print(f"  Connected clients: {ws_status['clients']}")

    print("\nServer is running. Use websocket_manager.lua to stop." if not use_signals else "\nServer is running. Press Ctrl+C to stop.")

    # Set up graceful shutdown
    stop_event = asyncio.Event()

    def signal_handler():
        print("\nShutting down...")
        stop_event.set()

    # Always register signal handlers (both modes need SIGTERM for clean shutdown)
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    # Wait for stop signal
    await stop_event.wait()

    # Clean shutdown
    await server.stop_websocket_server()
    print("Server stopped.")


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m src.main <path-to-als-or-xml> [OPTIONS]")
        print("\nModes:")
        print("  --mode=legacy     - Output raw dict AST (default)")
        print("  --mode=server     - Use AST server with node objects")
        print("  --mode=info       - Show project info summary")
        print("  --mode=websocket  - Start WebSocket server for web viewer")
        print("\nWebSocket Options:")
        print("  --ws-host=HOST    - WebSocket host (default: localhost)")
        print("  --ws-port=PORT    - WebSocket port (default: 8765)")
        print("  --no-signals      - Disable signal handlers (for hs.task)")
        sys.exit(1)

    path = Path(sys.argv[1])
    mode = "legacy"
    ws_host = "localhost"
    ws_port = 8765
    use_signals = True

    # Parse optional arguments
    if len(sys.argv) > 2:
        for arg in sys.argv[2:]:
            if arg.startswith("--mode="):
                mode = arg.split("=")[1]
            elif arg.startswith("--ws-host="):
                ws_host = arg.split("=")[1]
            elif arg.startswith("--ws-port="):
                ws_port = int(arg.split("=")[1])
            elif arg == "--no-signals":
                use_signals = False

    if mode == "websocket":
        # Run WebSocket server
        try:
            asyncio.run(run_websocket_server(path, ws_host, ws_port, use_signals))
        except KeyboardInterrupt:
            print("\nShutdown complete.")
    elif mode == "server" or mode == "info":
        # Use new AST server
        server = ASTServer()
        server.load_project(path)

        if mode == "info":
            # Show project info
            info = server.get_project_info()
            print(json.dumps(info, indent=2))
        else:
            # Show full AST
            print(server.get_ast_json())
    else:
        # Legacy mode: output raw dict
        tree = load_ableton_xml(path)
        ast = build_ast(tree.getroot())
        print(json.dumps(ast, indent=2))


if __name__ == "__main__":
    main()
