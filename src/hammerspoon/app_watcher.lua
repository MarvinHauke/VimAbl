-- Application watcher for Ableton Live
local statusCheck = require("status_check")
local liveState = require("live_state")
local wsManager = require("websocket_manager")

local M = {}

-- Keep watcher reference to prevent garbage collection
local appWatcher = nil

-- Application watcher callback to detect when Ableton starts
local function applicationWatcherCallback(appName, eventType, appObject)
	if appName == "Live" then
		if eventType == hs.application.watcher.launched then
			print("Ableton VimMode: Ableton launched, checking connection...")
			-- Try connection checks at 3s, 10s, and 20s intervals
			-- This handles cases where Remote Script loads slowly
			local attempts = { 3, 10, 20 }

			for _, delay in ipairs(attempts) do
				hs.timer.doAfter(delay, function()
					local success = statusCheck.checkConnection()
					if success then
						print("Ableton VimMode: Connection check succeeded after " .. delay .. " seconds")
					else
						print("Ableton VimMode: Connection check failed at " .. delay .. " seconds")
					end
				end)
			end

			-- Wait 5 seconds for Live to fully load, then start WebSocket server
			hs.timer.doAfter(5, function()
				print("Ableton VimMode: Attempting to start WebSocket server...")
				local projectPath = liveState.getProjectPath()
				if projectPath then
					print("Ableton VimMode: Found project: " .. projectPath)
					wsManager.start(projectPath)
				else
					print("Ableton VimMode: No project loaded in Ableton (this is normal for new projects)")
					print("Ableton VimMode: Save your project first, then use Cmd+Shift+W to start WebSocket server")
				end
			end)

		elseif eventType == hs.application.watcher.terminated then
			print("Ableton VimMode: Ableton closed")
			wsManager.stop()
		end
	end
end

function M.setup()
	-- Store watcher reference at module level to prevent garbage collection
	appWatcher = hs.application.watcher.new(applicationWatcherCallback)
	appWatcher:start()
	print("Ableton VimMode: Application watcher started")
end

function M.stop()
	if appWatcher then
		appWatcher:stop()
		print("Ableton VimMode: Application watcher stopped")
	end
end

return M
