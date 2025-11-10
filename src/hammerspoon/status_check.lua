-- Status check module for Ableton Live connection
local liveState = require("live_state")

local M = {}

-- Check if Ableton is running and server is responding
function M.checkConnection()
	local abletonApp = hs.application.find("Live")

	if not abletonApp then
		print("Ableton VimMode: Ableton not running")
		return false
	end

	-- Try to get state from server
	local state = liveState.getState()

	if state then
		hs.alert.show("Ableton VimMode connected! (" .. state.view .. " view)")
		return true
	else
		print("Ableton VimMode: Server not responding (Ableton is running but Remote Script may not be loaded)")
		return false
	end
end

return M
