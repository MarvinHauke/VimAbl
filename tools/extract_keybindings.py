#!/usr/bin/env python3
"""
Extract keybindings from Hammerspoon Lua files and generate markdown table.

Usage:
    python tools/extract_keybindings.py > docs/_auto-generated/keybindings-table.md
"""

import re
from pathlib import Path
from typing import List, Dict

def extract_keybindings_from_file(file_path: Path) -> List[Dict[str, str]]:
    """Extract keybinding definitions from a Lua file."""
    keybindings = []

    content = file_path.read_text()

    # Pattern for hs.hotkey.bind
    # Example: hs.hotkey.bind({"cmd"}, "y", function() ... end)
    hotkey_pattern = r'hs\.hotkey\.bind\(\{([^}]+)\},\s*"([^"]+)",\s*function\(\)(.*?)end\)'

    matches = re.finditer(hotkey_pattern, content, re.DOTALL)

    for match in matches:
        modifiers = match.group(1).strip()
        key = match.group(2)
        func_body = match.group(3)

        # Try to extract description from comments
        description = ""
        comment_match = re.search(r'--\s*(.+)', func_body)
        if comment_match:
            description = comment_match.group(1).strip()

        # Format keybinding
        mod_list = [m.strip().strip('"') for m in modifiers.split(',')]
        keybinding = '+'.join(mod_list) + '+' + key if mod_list else key

        keybindings.append({
            'keybinding': keybinding,
            'description': description or 'No description',
            'file': file_path.name
        })

    # Pattern for double-tap sequences (gg, dd, etc.)
    # Look for specific patterns like "gg" or "dd"
    sequence_pattern = r'["\'](gg|dd|za|G)["\']\s*--\s*(.+)'

    for match in re.finditer(sequence_pattern, content):
        sequence = match.group(1)
        description = match.group(2).strip()

        keybindings.append({
            'keybinding': sequence,
            'description': description,
            'file': file_path.name
        })

    return keybindings

def generate_markdown_table(keybindings: List[Dict[str, str]]) -> str:
    """Generate markdown table from keybindings."""
    if not keybindings:
        return "No keybindings found.\n"

    # Group by file
    by_file = {}
    for kb in keybindings:
        file = kb['file']
        if file not in by_file:
            by_file[file] = []
        by_file[file].append(kb)

    markdown = "# Auto-Generated Keybindings Reference\n\n"
    markdown += "*This file is auto-generated. Do not edit manually.*\n\n"

    for file, bindings in sorted(by_file.items()):
        markdown += f"## {file}\n\n"
        markdown += "| Keybinding | Description |\n"
        markdown += "|------------|-------------|\n"

        for kb in sorted(bindings, key=lambda x: x['keybinding']):
            markdown += f"| `{kb['keybinding']}` | {kb['description']} |\n"

        markdown += "\n"

    return markdown

def main():
    """Main function to extract and print keybindings."""
    # Find all Lua files in src/hammerspoon/keys/
    keys_dir = Path("src/hammerspoon/keys")

    if not keys_dir.exists():
        print("Error: src/hammerspoon/keys/ directory not found")
        return

    all_keybindings = []

    for lua_file in keys_dir.glob("*.lua"):
        keybindings = extract_keybindings_from_file(lua_file)
        all_keybindings.extend(keybindings)

    # Also check main files
    for lua_file in ["src/hammerspoon/ableton.lua", "src/hammerspoon/websocket_manager.lua"]:
        path = Path(lua_file)
        if path.exists():
            keybindings = extract_keybindings_from_file(path)
            all_keybindings.extend(keybindings)

    markdown = generate_markdown_table(all_keybindings)
    print(markdown)

if __name__ == "__main__":
    main()
