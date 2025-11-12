#!/usr/bin/env python3
"""Simple WebSocket client to test the server."""

import asyncio
import json
import websockets


async def test_connection():
    """Test connecting to the WebSocket server."""
    uri = "ws://localhost:8765"

    print(f"Connecting to {uri}...")

    try:
        async with websockets.connect(uri) as websocket:
            print("Connected!")

            # Wait for initial message
            message = await websocket.recv()
            data = json.loads(message)

            print(f"\nReceived message type: {data.get('type')}")

            if data.get('type') == 'FULL_AST':
                ast = data.get('payload', {}).get('ast', {})
                print(f"AST root type: {ast.get('node_type')}")
                print(f"AST root hash: {ast.get('hash', '')[:16]}...")
                print(f"Number of children: {len(ast.get('children', []))}")

                # Print first few children
                for i, child in enumerate(ast.get('children', [])[:3]):
                    print(f"  Child {i}: {child.get('node_type')} - {child.get('attributes', {}).get('name', 'N/A')}")
            elif data.get('type') == 'ERROR':
                error = data.get('payload', {})
                print(f"Error: {error.get('error')}")
                print(f"Details: {error.get('details')}")

            print("\nTest successful!")

    except ConnectionRefusedError:
        print("Error: Could not connect to server. Is it running?")
        print("Start the server with: python3 -m src.main Example_Project/example.als --mode=websocket")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_connection())
