-- Quick test script for debugging commands
-- Run this from Hammerspoon console with: dofile("path/to/test_commands.lua")

local liveState = require("live_state")

print("\n=== Testing Live State Commands ===")

print("\n1. Testing GET_VIEW:")
local view = liveState.getCurrentView()
print("Current view: " .. tostring(view))

print("\n2. Testing JUMP_TO_FIRST (auto-detects view):")
local result = liveState.jumpToFirst()
print("Result: " .. tostring(result))

print("\n3. Testing JUMP_TO_LAST (auto-detects view):")
result = liveState.jumpToLast()
print("Result: " .. tostring(result))

print("\n4. Testing GET_STATE:")
local state = liveState.getState()
if state then
	print("View: " .. tostring(state.view))
	print("Transport playing: " .. tostring(state.transport_playing))
	print("Browser visible: " .. tostring(state.browser_visible))
else
	print("Failed to get state")
end

print("\n=== Tests Complete ===\n")
