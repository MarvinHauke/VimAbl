This Repo contains LSP like Server funktions for Ableton Live.
It will also add some vim like keebindgs for faster and more intuitive useabilty of Ableton Live.

# Dependencies

karabiner elements
hammerspoon
Ableton Live

# Architecture:

Karabiner elements will be used for catching keyboard shortcuts on kernel level.
After that they will be passed further to Hammerspoon which will launch a local server
for interactions with ableton live via remote scripts.

# Ideas:

- Overlay for fast navigation and command mode.
- Ability to use Plugins written in lua by users for additional functionality.
- Ki implementation with different models, for auto completion styles of different generes.
