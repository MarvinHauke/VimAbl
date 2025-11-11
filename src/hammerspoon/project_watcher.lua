-- Project file watcher - detects when .als files are saved
local wsManager = require("websocket_manager")
local config = require("config")

local M = {}

M.watchers = {}  -- Keep track of active watchers
M.lastDetectedProject = nil
M.lastDetectionTime = 0  -- Timestamp of last detection
M.activeProjectDir = nil  -- Directory of the currently active project
M.isNarrowMode = false  -- Whether we're in narrow (single project) mode
M.switchTimer = nil  -- Timer for debouncing mode switches
M.startTimer = nil  -- Timer for debouncing WebSocket starts

-- Maximum number of watchers to prevent resource exhaustion
local MAX_WATCHERS = 100

-- Recursively find all subdirectories
local function findSubdirectories(dir, maxDepth, currentDepth, totalCount)
	currentDepth = currentDepth or 0
	maxDepth = maxDepth or 1  -- Default max depth: just immediate subdirectories
	totalCount = totalCount or {count = 0}  -- Track total directories found

	local subdirs = {dir}  -- Include the directory itself
	totalCount.count = totalCount.count + 1

	-- Safety limit: stop if we've found too many directories
	if totalCount.count >= MAX_WATCHERS then
		print("[ProjectWatcher] Warning: Reached maximum directory limit (" .. MAX_WATCHERS .. ")")
		return subdirs
	end

	if currentDepth >= maxDepth then
		return subdirs
	end

	-- Use pcall to safely handle file system errors
	local success, iter, dirObj = pcall(hs.fs.dir, dir)
	if not success or not iter then
		return subdirs
	end

	-- Collect entries first, then close iterator
	local entries = {}
	for entry in iter, dirObj do
		if entry ~= "." and entry ~= ".." then
			table.insert(entries, entry)
		end
	end

	-- Process entries
	for _, entry in ipairs(entries) do
		local fullPath = dir .. "/" .. entry
		local success, attrs = pcall(hs.fs.attributes, fullPath)

		-- Check if it's a directory and not hidden
		if success and attrs and attrs.mode == "directory" and not entry:match("^%.") then
			-- Skip common Ableton backup/cache folders
			if entry == "Backup" or entry == "Ableton Project Info" or entry == "Samples" or entry:match("^Recorded") then
				-- Skip these folders
				goto skip_entry
			end

			-- Recursively find subdirectories
			local deeperDirs = findSubdirectories(fullPath, maxDepth, currentDepth + 1, totalCount)
			for _, subdir in ipairs(deeperDirs) do
				if totalCount.count < MAX_WATCHERS then
					table.insert(subdirs, subdir)
					totalCount.count = totalCount.count + 1
				end
			end
		end
		::skip_entry::
	end

	return subdirs
end

-- Switch to narrow mode: watch only the specific project directory
local function switchToNarrowMode(projectPath)
	-- Extract directory from project file path
	local projectDir = projectPath:match("(.*/)")
	if not projectDir then
		print("[ProjectWatcher] Could not extract directory from: " .. projectPath)
		return
	end

	-- Remove trailing slash for comparison
	projectDir = projectDir:gsub("/$", "")

	-- If already watching this directory, don't switch again
	if M.isNarrowMode and M.activeProjectDir == projectDir then
		print("[ProjectWatcher] Already in narrow mode for: " .. projectDir)
		return
	end

	-- Cancel any pending switch
	if M.switchTimer then
		M.switchTimer:stop()
	end

	-- Debounce the switch to avoid rapid mode changes
	M.switchTimer = hs.timer.doAfter(1, function()
		print("[ProjectWatcher] Switching to narrow mode for: " .. projectDir)

		M.activeProjectDir = projectDir
		M.isNarrowMode = true

		-- Stop all watchers and watch only the project directory
		M.stop()

		local success, watcher = pcall(hs.pathwatcher.new, projectDir, onFileChanged)
		if success and watcher then
			local startSuccess = pcall(function() return watcher:start() end)
			if startSuccess then
				table.insert(M.watchers, watcher)
				print("[ProjectWatcher] Now watching only: " .. projectDir)
			end
		end
	end)
end

-- Callback when a file changes in watched directory
local function onFileChanged(paths, flagTables)
	for i, path in ipairs(paths) do
		-- Check if it's an .als file
		if path:match("%.als$") then
			-- Ignore backup files (in Backup/ or Ableton Project Info/ folders)
			if path:match("/Backup/") or path:match("/Ableton Project Info/") then
				-- Silently ignore backup files
				goto continue
			end

			local flags = flagTables[i]

			-- Check if file was created or modified (itemCreated, itemModified, or itemRenamed)
			if flags.itemCreated or flags.itemModified or flags.itemRenamed then
				print("[ProjectWatcher] Detected .als file change: " .. path)

				-- Debounce: Only trigger if it's a different project or enough time has passed (3 seconds)
				local now = hs.timer.secondsSinceEpoch()
				local timeSinceLastDetection = now - M.lastDetectionTime

				if path ~= M.lastDetectedProject or timeSinceLastDetection > 3 then
					M.lastDetectedProject = path
					M.lastDetectionTime = now
					print("[ProjectWatcher] New project detected, starting WebSocket server...")

					-- Cancel any pending start
					if M.startTimer then
						M.startTimer:stop()
					end

					-- Short delay to ensure file is fully written (0.5 seconds)
					M.startTimer = hs.timer.doAfter(0.5, function()
						wsManager.start(path)
						-- After successful save, switch to narrow mode
						switchToNarrowMode(path)
					end)
				else
					print("[ProjectWatcher] Ignoring duplicate detection (within 3 seconds)")
				end
			end
		end
		::continue::
	end
end

-- Start watching directories
function M.start()
	print("[ProjectWatcher] Starting directory watchers...")

	-- Stop any existing watchers
	M.stop()

	-- If we have an active project, watch only that directory (narrow mode)
	if M.isNarrowMode and M.activeProjectDir then
		print("[ProjectWatcher] Using narrow mode for active project: " .. M.activeProjectDir)

		local success, watcher = pcall(hs.pathwatcher.new, M.activeProjectDir, onFileChanged)
		if success and watcher then
			local startSuccess = pcall(function() return watcher:start() end)
			if startSuccess then
				table.insert(M.watchers, watcher)
				print("[ProjectWatcher] Watching 1 directory (narrow mode)")
				return
			end
		end

		-- If narrow mode failed, fall back to broad mode
		print("[ProjectWatcher] Narrow mode failed, falling back to broad mode")
		M.isNarrowMode = false
		M.activeProjectDir = nil
	end

	-- Broad mode: scan recursively for projects
	print("[ProjectWatcher] Using broad mode (scanning subdirectories)")

	-- Use directories from config
	local watchDirs = config.projectWatchDirs or {}

	for _, dir in ipairs(watchDirs) do
		-- Check if directory exists
		local dirExists = hs.fs.attributes(dir)
		if dirExists then
			print("[ProjectWatcher] Scanning: " .. dir)

			-- Find all subdirectories recursively (max depth 1 - just project folders)
			local success, allDirs = pcall(findSubdirectories, dir, 1)
			if not success then
				print("[ProjectWatcher] Error scanning directory: " .. dir)
				print("[ProjectWatcher] Error: " .. tostring(allDirs))
			else
				print("[ProjectWatcher] Found " .. #allDirs .. " directories to watch under: " .. dir)

				-- Create a watcher for each subdirectory
				for _, subdir in ipairs(allDirs) do
					-- Limit total watchers
					if #M.watchers >= MAX_WATCHERS then
						print("[ProjectWatcher] Reached maximum watcher limit, stopping")
						break
					end

					-- Try to create watcher with error handling
					local watcherSuccess, watcher = pcall(hs.pathwatcher.new, subdir, onFileChanged)
					if watcherSuccess and watcher then
						local startSuccess, startErr = pcall(function() return watcher:start() end)
						if startSuccess then
							table.insert(M.watchers, watcher)
						else
							print("[ProjectWatcher] Failed to start watcher for: " .. subdir)
						end
					else
						print("[ProjectWatcher] Failed to create watcher for: " .. subdir)
					end
				end
			end
		else
			print("[ProjectWatcher] Directory not found, skipping: " .. dir)
		end
	end

	print("[ProjectWatcher] Watching " .. #M.watchers .. " directories for .als files (broad mode)")
end

-- Stop all watchers
function M.stop()
	for _, watcher in ipairs(M.watchers) do
		watcher:stop()
	end
	M.watchers = {}
	print("[ProjectWatcher] Stopped all directory watchers")
end

-- Switch back to broad mode (scan all directories)
function M.switchToBroadMode()
	print("[ProjectWatcher] Switching to broad mode")
	M.isNarrowMode = false
	M.activeProjectDir = nil
	M.lastDetectedProject = nil
	M.start()
end

-- Add a directory to watch
function M.addWatchDir(dir)
	-- Check if already in config
	for _, watched in ipairs(config.projectWatchDirs) do
		if watched == dir then
			print("[ProjectWatcher] Already in config: " .. dir)
			return
		end
	end

	-- Add to config
	table.insert(config.projectWatchDirs, dir)

	-- Start watching if directory exists
	local dirExists = hs.fs.attributes(dir)
	if dirExists then
		print("[ProjectWatcher] Adding watchers for: " .. dir)

		-- Find all subdirectories recursively
		local success, allDirs = pcall(findSubdirectories, dir, 1)
		if not success then
			print("[ProjectWatcher] Error scanning directory: " .. dir)
			print("[ProjectWatcher] Error: " .. tostring(allDirs))
		else
			print("[ProjectWatcher] Found " .. #allDirs .. " directories to watch")

			-- Create watchers for all subdirectories
			for _, subdir in ipairs(allDirs) do
				-- Limit total watchers
				if #M.watchers >= MAX_WATCHERS then
					print("[ProjectWatcher] Reached maximum watcher limit, stopping")
					break
				end

				-- Try to create watcher with error handling
				local watcherSuccess, watcher = pcall(hs.pathwatcher.new, subdir, onFileChanged)
				if watcherSuccess and watcher then
					local startSuccess = pcall(function() return watcher:start() end)
					if startSuccess then
						table.insert(M.watchers, watcher)
					else
						print("[ProjectWatcher] Failed to start watcher for: " .. subdir)
					end
				else
					print("[ProjectWatcher] Failed to create watcher for: " .. subdir)
				end
			end
		end
	else
		print("[ProjectWatcher] Directory not found: " .. dir)
	end
end

-- Get status
function M.getStatus()
	return {
		watching = #M.watchers > 0,
		mode = M.isNarrowMode and "narrow" or "broad",
		directories = config.projectWatchDirs,
		activeProjectDir = M.activeProjectDir,
		activeWatchers = #M.watchers,
		lastProject = M.lastDetectedProject,
	}
end

return M
