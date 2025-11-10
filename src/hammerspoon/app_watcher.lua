-- Application watcher for Ableton Live
local statusCheck = require("status_check")

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
		elseif eventType == hs.application.watcher.terminated then
			print("Ableton VimMode: Ableton closed")
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
