import asyncio
import websockets
import json
import sys

async def listen():
    uri = "ws://localhost:8765"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected to {uri}")
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get('type')
                    if msg_type == 'full_ast':
                         print("Received: full_ast (Initial Load)")
                    elif msg_type == 'DIFF_UPDATE':
                         changes = data.get('payload', {}).get('diff', {}).get('changes', [])
                         if not changes:
                             changes = data.get('payload', {}).get('changes', []) # Fallback
                         
                         print(f"Received: DIFF_UPDATE with {len(changes)} changes")
                         for change in changes:
                             print(f"  - Change: {change.get('type')} on {change.get('path')} (Action: {change.get('action')})")
                    else:
                        print(f"Received: {msg_type}")
                except json.JSONDecodeError:
                    print("Received non-JSON message")
    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(listen())
    except KeyboardInterrupt:
        pass
