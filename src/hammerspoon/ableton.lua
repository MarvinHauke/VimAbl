-- Main Ableton Live integration entry point
-- This file loads all keybinding modules

local M = {}

-- Load all keybinding modules
local navigation = require("keys.navigation")
local editing = require("keys.editing")
local views = require("keys.views")
local statusCheck = require("status_check")
local appWatcher = require("app_watcher")

-- Setup all keybindings
navigation.setup()
editing.setup()
views.setup()

-- Setup application watcher
appWatcher.setup()

-- Check connection status on initial load
statusCheck.checkConnection()

return M
