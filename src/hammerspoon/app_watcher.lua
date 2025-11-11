-- Application watcher for Ableton Live
local statusCheck = require("status_check")
local liveState = require("live_state")
local wsManager = require("websocket_manager")
local projectWatcher = require("project_watcher")

local M = {}

-- Keep watcher reference to prevent garbage collection
local appWatcher = nil

-- Smart connection checker with exponential backoff
local connectionTimer = nil
local function checkConnectionWithBackoff(attempt, maxAttempts, startTime)
	attempt = attempt or 1
	maxAttempts = maxAttempts or 10
	startTime = startTime or hs.timer.secondsSinceEpoch()

	local success = statusCheck.checkConnection()
	local elapsed = hs.timer.secondsSinceEpoch() - startTime

	if success then
		-- Connection successful!
		print(string.format("Ableton VimMode: Connection established after %.1fs (attempt %d)", elapsed, attempt))
		if connectionTimer then
			connectionTimer:stop()
			connectionTimer = nil
		end
		return
	end

	-- Connection failed
	if attempt == 1 then
		print(string.format("Ableton VimMode: Connection check failed at %.1fs", elapsed))
	end

	-- Stop if we've reached max attempts
	if attempt >= maxAttempts then
		print(string.format("Ableton VimMode: Gave up after %d attempts (%.1fs)", maxAttempts, elapsed))
		if connectionTimer then
			connectionTimer:stop()
			connectionTimer = nil
		end
		return
	end

	-- Calculate next delay with exponential backoff
	-- Start with 0.5s checks, gradually increase to 3s
	local nextDelay
	if attempt <= 3 then
		nextDelay = 0.5  -- First 3 attempts: every 0.5s (covers 5s-6.5s)
	elseif attempt <= 6 then
		nextDelay = 1    -- Next 3 attempts: every 1s (covers 6.5s-9.5s)
	else
		nextDelay = 2    -- Remaining attempts: every 2s (covers 9.5s-17.5s)
	end

	-- Schedule next check
	connectionTimer = hs.timer.doAfter(nextDelay, function()
		checkConnectionWithBackoff(attempt + 1, maxAttempts, startTime)
	end)
end

-- Application watcher callback to detect when Ableton starts
local function applicationWatcherCallback(appName, eventType, appObject)
	if appName == "Live" then
		if eventType == hs.application.watcher.launched then
			print("Ableton VimMode: Ableton launched, checking connection...")

			-- Wait 5 seconds before starting connection checks (Remote Script needs time to load)
			hs.timer.doAfter(5, function()
				checkConnectionWithBackoff()
			end)

			-- Start watching directories for .als file saves
			hs.timer.doAfter(2, function()
				print("Ableton VimMode: Starting project file watcher...")
				projectWatcher.start()
				print("Ableton VimMode: Watching for .als file saves. Save your project (Cmd+S) to auto-start the server.")
			end)

		elseif eventType == hs.application.watcher.terminated then
			print("Ableton VimMode: Ableton closed")
			-- Stop connection checker if running
			if connectionTimer then
				connectionTimer:stop()
				connectionTimer = nil
			end
			projectWatcher.stop()
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
