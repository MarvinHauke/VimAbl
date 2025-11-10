#!/bin/bash

# symlink.sh - Links all Hammerspoon Lua files to ~/.hammerspoon/
# This allows the Hammerspoon app to load the VimAbl integration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HAMMERSPOON_DIR="$HOME/.hammerspoon"

echo "VimAbl Hammerspoon Symlink Setup"
echo "================================="
echo ""

# Create ~/.hammerspoon directory if it doesn't exist
if [ ! -d "$HAMMERSPOON_DIR" ]; then
    echo "Creating $HAMMERSPOON_DIR directory..."
    mkdir -p "$HAMMERSPOON_DIR"
fi

# Function to create or update symlink
create_symlink() {
    local source=$1
    local target=$2
    local name=$(basename "$source")

    if [ -L "$target" ]; then
        # If it's already a symlink, check if it points to the right place
        local current_target=$(readlink "$target")
        if [ "$current_target" = "$source" ]; then
            echo "  ✓ $name (already linked)"
        else
            echo "  → $name (updating symlink)"
            ln -sf "$source" "$target"
        fi
    elif [ -e "$target" ]; then
        # If a file/directory exists but isn't a symlink, warn the user
        echo "  ⚠ $name (file exists, skipping - please backup and remove manually)"
    else
        # Create new symlink
        echo "  + $name (creating symlink)"
        ln -s "$source" "$target"
    fi
}

echo "Linking Lua files..."

# Link all .lua files in the hammerspoon directory
for lua_file in "$SCRIPT_DIR"/*.lua; do
    if [ -f "$lua_file" ]; then
        create_symlink "$lua_file" "$HAMMERSPOON_DIR/$(basename "$lua_file")"
    fi
done

# Link the keys directory
if [ -d "$SCRIPT_DIR/keys" ]; then
    create_symlink "$SCRIPT_DIR/keys" "$HAMMERSPOON_DIR/keys"
fi

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Make sure Hammerspoon is installed (brew install --cask hammerspoon)"
echo "2. Add this line to your ~/.hammerspoon/init.lua:"
echo "   require('ableton')"
echo "3. Reload Hammerspoon configuration"
echo ""
