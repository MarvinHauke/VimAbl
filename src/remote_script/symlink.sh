#!/bin/bash

# symlink.sh - Links Remote Script to Ableton Live's User Remote Scripts
# This allows Ableton Live to load the VimAbl Remote Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="VimAbl"

# Detect the current user's home directory
USER_HOME="$HOME"

echo "VimAbl Remote Script Symlink Setup"
echo "==================================="
echo ""
echo "User: $(whoami)"
echo "Home: $USER_HOME"
echo ""

# Auto-detect Ableton Live installation (prefer User Library location)
ABLETON_REMOTE_SCRIPTS=""

# Check for User Library location (preferred - works across all Live versions)
if [ -d "$USER_HOME/Music/Ableton/User Library/Remote Scripts" ]; then
    ABLETON_REMOTE_SCRIPTS="$USER_HOME/Music/Ableton/User Library/Remote Scripts"
    echo "✓ Using User Library location"
    echo "  Location: $ABLETON_REMOTE_SCRIPTS"
    echo ""
# Fallback to Preferences location for Live 12+ (if User Library doesn't exist)
elif [ -d "$USER_HOME/Library/Preferences/Ableton" ]; then
    # Find the most recent Live 12.x directory
    LIVE_DIR=$(find "$USER_HOME/Library/Preferences/Ableton" -maxdepth 1 -type d -name "Live 12*" | sort -V | tail -1)

    if [ -n "$LIVE_DIR" ]; then
        ABLETON_REMOTE_SCRIPTS="$LIVE_DIR/User Remote Scripts"
        echo "✓ Found: $(basename "$LIVE_DIR")"
        echo "  Location: $LIVE_DIR"
        echo ""
    fi
fi

# Error if no Ableton installation found
if [ -z "$ABLETON_REMOTE_SCRIPTS" ]; then
    echo "❌ Error: Could not find Ableton Live installation"
    echo ""
    echo "Searched locations:"
    echo "  • $USER_HOME/Library/Preferences/Ableton/Live 12*"
    echo "  • $USER_HOME/Music/Ableton/User Library"
    echo ""
    echo "Please make sure:"
    echo "1. Ableton Live is installed"
    echo "2. You've run Ableton Live at least once"
    echo ""
    exit 1
fi

echo "Target: $ABLETON_REMOTE_SCRIPTS/$PROJECT_NAME"
echo ""

# Create Remote Scripts directory if it doesn't exist
if [ ! -d "$ABLETON_REMOTE_SCRIPTS" ]; then
    echo "Creating Remote Scripts directory..."
    mkdir -p "$ABLETON_REMOTE_SCRIPTS"
fi

TARGET_DIR="$ABLETON_REMOTE_SCRIPTS/$PROJECT_NAME"

# Handle existing installation
if [ -L "$TARGET_DIR" ]; then
    # If it's already a symlink, check if it points to the right place
    current_target=$(readlink "$TARGET_DIR")
    if [ "$current_target" = "$SCRIPT_DIR" ]; then
        echo "✓ Remote Script already linked correctly"
        echo ""
        echo "Next steps:"
        echo "1. Restart Ableton Live (quit and reopen)"
        echo "2. Go to Preferences → Link/Tempo/MIDI → MIDI"
        echo "3. Select 'VimAbl' as a Control Surface"
        echo "4. Set both Input and Output to 'None'"
        echo ""
        exit 0
    else
        echo "→ Updating existing symlink..."
        echo "  Old target: $current_target"
        echo "  New target: $SCRIPT_DIR"
        rm "$TARGET_DIR"
        ln -s "$SCRIPT_DIR" "$TARGET_DIR"
    fi
elif [ -e "$TARGET_DIR" ]; then
    # If a directory exists but isn't a symlink, warn the user
    echo "⚠ Warning: A directory already exists at:"
    echo "   $TARGET_DIR"
    echo ""
    echo "Please backup and remove it manually, then run this script again."
    echo ""
    echo "Suggested commands:"
    echo "  mv '$TARGET_DIR' '$TARGET_DIR.backup'"
    echo "  ./symlink.sh"
    echo ""
    exit 1
else
    # Create new symlink
    echo "+ Creating symlink..."
    ln -s "$SCRIPT_DIR" "$TARGET_DIR"
fi

echo ""
echo "✓ Setup complete!"
echo ""
echo "Files and directories linked:"
for file in "$SCRIPT_DIR"/*.py; do
    if [ -f "$file" ]; then
        echo "  • $(basename "$file")"
    fi
done
for dir in "$SCRIPT_DIR"/_*; do
    if [ -d "$dir" ]; then
        echo "  • $(basename "$dir")/ (directory)"
    fi
done

echo ""
echo "Next steps:"
echo "1. Restart Ableton Live (quit and reopen, not just MIDI reload)"
echo "2. Go to Preferences → Link/Tempo/MIDI → MIDI"
echo "3. In the Control Surface dropdown, select 'VimAbl'"
echo "4. Set both Input and Output to 'None'"
echo "5. The socket server will start on port 9001"
echo "6. Check Hammerspoon integration with the status_check module"
echo ""
