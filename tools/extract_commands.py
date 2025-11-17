#!/usr/bin/env python3
"""
Extract TCP commands from LiveState.py and generate markdown table.

Usage:
    python tools/extract_commands.py > docs/_auto-generated/commands-table.md
"""

import re
from pathlib import Path
from typing import List, Dict

def extract_commands(file_path: Path) -> List[Dict[str, str]]:
    """Extract command definitions from LiveState.py."""
    commands = []

    if not file_path.exists():
        return commands

    content = file_path.read_text()

    # Pattern for command handlers
    # Example: def _handle_get_view(self, params=None):
    handler_pattern = r'def\s+_handle_(\w+)\(self,\s*params=None\):\s*"""(.+?)"""'

    matches = re.finditer(handler_pattern, content, re.DOTALL)

    for match in matches:
        command_name = match.group(1).upper()
        docstring = match.group(2).strip()

        # Extract first line of docstring as description
        description = docstring.split('\n')[0].strip()

        commands.append({
            'command': command_name,
            'description': description
        })

    # Also look for command registration
    # Pattern: "COMMAND_NAME": self._handle_command,
    registration_pattern = r'"([A-Z_]+)":\s*self\._handle_\w+'

    registered_commands = set()
    for match in re.finditer(registration_pattern, content):
        registered_commands.add(match.group(1))

    # Add any registered commands not found via docstrings
    for cmd in registered_commands:
        if not any(c['command'] == cmd for c in commands):
            commands.append({
                'command': cmd,
                'description': 'No description available'
            })

    return sorted(commands, key=lambda x: x['command'])

def generate_markdown_table(commands: List[Dict[str, str]]) -> str:
    """Generate markdown table from commands."""
    if not commands:
        return "No commands found.\n"

    markdown = "# Auto-Generated Commands Reference\n\n"
    markdown += "*This file is auto-generated. Do not edit manually.*\n\n"
    markdown += "## TCP Socket Commands (Port 9001)\n\n"
    markdown += "| Command | Description |\n"
    markdown += "|---------|-------------|\n"

    for cmd in commands:
        markdown += f"| `{cmd['command']}` | {cmd['description']} |\n"

    markdown += "\n"
    markdown += "## Usage\n\n"
    markdown += "```bash\n"
    markdown += "echo \"COMMAND_NAME\" | nc 127.0.0.1 9001\n"
    markdown += "```\n"

    return markdown

def main():
    """Main function to extract and print commands."""
    file_path = Path("src/remote_script/commands.py")

    if not file_path.exists():
        # Fallback to LiveState.py
        file_path = Path("src/remote_script/LiveState.py")
        if not file_path.exists():
            print("Error: Command files not found")
            return

    commands = extract_commands(file_path)
    markdown = generate_markdown_table(commands)
    print(markdown)

if __name__ == "__main__":
    main()
