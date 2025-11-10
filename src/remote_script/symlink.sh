#!/bin/bash

# symlink.sh - Links Remote Script to Ableton Live's User Library
# This allows Ableton Live to load the VimAbl Remote Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="VimAbl"

# Detect the current user's home directory
USER_HOME="$HOME"

# Construct the Ableton User Library path
ABLETON_REMOTE_SCRIPTS="$USER_HOME/Music/Ableton/User Library/Remote Scripts"

echo "VimAbl Remote Script Symlink Setup"
echo "==================================="
echo ""
echo "User: $(whoami)"
echo "Home: $USER_HOME"
echo "Target: $ABLETON_REMOTE_SCRIPTS/$PROJECT_NAME"
echo ""

# Check if the Ableton User Library exists
if [ ! -d "$USER_HOME/Music/Ableton/User Library" ]; then
    echo "❌ Error: Ableton User Library not found at:"
    echo "   $USER_HOME/Music/Ableton/User Library"
    echo ""
    echo "Please make sure:"
    echo "1. Ableton Live is installed"
    echo "2. You've run Ableton Live at least once (to create the User Library)"
    echo "3. The User Library path is correct for your system"
    echo ""
    exit 1
fi

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
        echo "1. Restart Ableton Live"
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
echo "Files linked:"
for file in "$SCRIPT_DIR"/*.py; do
    if [ -f "$file" ]; then
        echo "  • $(basename "$file")"
    fi
done

echo ""
echo "Next steps:"
echo "1. Restart Ableton Live (or quit and reopen)"
echo "2. Go to Preferences → Link/Tempo/MIDI → MIDI"
echo "3. In the Control Surface dropdown, select 'VimAbl'"
echo "4. Set both Input and Output to 'None'"
echo "5. The socket server will start on port 9001"
echo "6. Check Hammerspoon integration with the status_check module"
echo ""
