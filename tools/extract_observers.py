#!/usr/bin/env python3
"""
Extract observer event definitions from observers.py and generate markdown table.

Usage:
    python tools/extract_observers.py > docs/_auto-generated/observers-table.md
"""

import re
from pathlib import Path
from typing import List, Dict

def extract_osc_events(file_path: Path) -> List[Dict[str, str]]:
    """Extract OSC event paths from observers.py."""
    events = []

    if not file_path.exists():
        return events

    content = file_path.read_text()

    # Pattern for UDP send calls
    # Example: self.udp.send("/live/track/renamed", [track_idx, name])
    send_pattern = r'self\.udp\.send\("(/live/[^"]+)",\s*\[([^\]]+)\]'

    matches = re.finditer(send_pattern, content)

    for match in matches:
        event_path = match.group(1)
        args = match.group(2).strip()

        # Try to find context/comment before this line
        # Look for class definition or method name
        context_pattern = r'class\s+(\w+Observer)|def\s+(\w+)\(self'
        context_match = None

        # Search backwards from match position
        before_match = content[:match.start()]
        for ctx_match in re.finditer(context_pattern, before_match):
            context_match = ctx_match

        observer_class = ""
        if context_match:
            observer_class = context_match.group(1) or context_match.group(2)

        events.append({
            'event_path': event_path,
            'arguments': args,
            'observer': observer_class
        })

    return events

def generate_markdown_table(events: List[Dict[str, str]]) -> str:
    """Generate markdown table from OSC events."""
    if not events:
        return "No OSC events found.\n"

    # Group by observer class
    by_observer = {}
    for event in events:
        obs = event['observer'] or "Unknown"
        if obs not in by_observer:
            by_observer[obs] = []
        by_observer[obs].append(event)

    markdown = "# Auto-Generated Observers Reference\n\n"
    markdown += "*This file is auto-generated. Do not edit manually.*\n\n"
    markdown += "## UDP/OSC Events (Port 9002)\n\n"

    for observer, event_list in sorted(by_observer.items()):
        markdown += f"### {observer}\n\n"
        markdown += "| Event Path | Arguments |\n"
        markdown += "|------------|----------|\n"

        for event in sorted(event_list, key=lambda x: x['event_path']):
            markdown += f"| `{event['event_path']}` | `{event['arguments']}` |\n"

        markdown += "\n"

    return markdown

def main():
    """Main function to extract and print observers."""
    file_path = Path("src/remote_script/observers.py")

    if not file_path.exists():
        print("Error: src/remote_script/observers.py not found")
        return

    events = extract_osc_events(file_path)
    markdown = generate_markdown_table(events)
    print(markdown)

if __name__ == "__main__":
    main()
