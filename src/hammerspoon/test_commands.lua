-- Quick test script for debugging commands
-- Run this from Hammerspoon console with: dofile("path/to/test_commands.lua")

local liveState = require("live_state")

print("\n=== Testing Live State Commands ===")

print("\n1. Testing GET_VIEW:")
local view = liveState.getCurrentView()
print("Current view: " .. tostring(view))

print("\n2. Testing SELECT_FIRST_TRACK:")
local result = liveState.selectFirstTrack()
print("Result: " .. tostring(result))

print("\n3. Testing SELECT_LAST_TRACK:")
result = liveState.selectLastTrack()
print("Result: " .. tostring(result))

print("\n4. Testing SELECT_FIRST_SCENE:")
result = liveState.selectFirstScene()
print("Result: " .. tostring(result))

print("\n5. Testing SELECT_LAST_SCENE:")
result = liveState.selectLastScene()
print("Result: " .. tostring(result))

print("\n=== Tests Complete ===\n")
