-- WebSocket server manager for VimAbl TreeViewer
local M = {}
local liveState = require("live_state")

M.wsTask = nil
M.port = 8765
M.projectPath = nil
M.xmlPath = nil
M.fileWatcher = nil

-- Callback when .als file changes
local function onFileChanged(paths)
	for _, path in ipairs(paths) do
		print("[WebSocket] Project file changed: " .. path)
	end
	print("[WebSocket] Reloading AST and restarting server...")
	M.restart()
end

-- Export XML with retry logic (minimal retries since we pass path directly)
local function exportXMLWithRetry(projectPath, maxRetries, retryDelay)
	maxRetries = maxRetries or 2  -- Reduced from 3 to 2
	retryDelay = retryDelay or 0.5  -- Reduced from 1s to 0.5s

	for attempt = 1, maxRetries do
		if attempt > 1 then
			print(string.format("[WebSocket] Retry %d/%d after %.1fs...", attempt - 1, maxRetries - 1, retryDelay))
			os.execute(string.format("sleep %.1f", retryDelay))
		end

		local xmlPath, exportError = liveState.exportXML(projectPath)
		if xmlPath then
			print("[WebSocket] XML exported to: " .. xmlPath)
			return xmlPath, nil
		end

		print(string.format("[WebSocket] Export attempt %d failed: %s", attempt, exportError or "unknown error"))
	end

	return nil, "Failed after " .. maxRetries .. " attempts"
end

-- Start WebSocket server for a project
function M.start(projectPath)
	M.stop() -- Stop any existing server

	if not projectPath then
		print("[WebSocket] No project path provided")
		return false
	end

	M.projectPath = projectPath

	-- Export project as XML to .vimabl directory (with minimal retries)
	print("[WebSocket] Exporting project to XML...")
	local xmlPath, exportError = exportXMLWithRetry(projectPath, 2, 0.5)
	if not xmlPath then
		print("[WebSocket] ERROR: Failed to export XML: " .. (exportError or "unknown error"))
		return false
	end
	M.xmlPath = xmlPath

	-- Set up file watcher for the .als file (will trigger re-export and restart)
	M.startFileWatcher(projectPath)

	-- Find uv executable (check common locations)
	local uvPath = nil
	local possiblePaths = {
		os.getenv("HOME") .. "/.local/bin/uv",
		"/usr/local/bin/uv",
		"/opt/homebrew/bin/uv",
		hs.execute("which uv 2>/dev/null"):gsub("%s+", "")
	}

	for _, path in ipairs(possiblePaths) do
		if path ~= "" and hs.fs.attributes(path) then
			uvPath = path
			print("[WebSocket] Found uv at: " .. uvPath)
			break
		end
	end

	if not uvPath then
		print("[WebSocket] ERROR: uv not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh")
		return false
	end

	local projectRoot = os.getenv("HOME") .. "/Development/python/VimAbl"

	print("[WebSocket] Starting server for XML: " .. M.xmlPath)

	M.wsTask = hs.task.new(
		uvPath,
		function(exitCode, stdOut, stdErr)
			if exitCode == 0 then
				print("[WebSocket] Server stopped cleanly")
			else
				print("[WebSocket] Server error (exit code " .. exitCode .. "): " .. (stdErr or ""))
			end
		end,
		function(task, stdOut, stdErr)
			-- Stream output to console
			if stdOut and stdOut ~= "" then
				print("[WebSocket] " .. stdOut)
			end
			if stdErr and stdErr ~= "" then
				print("[WebSocket ERROR] " .. stdErr)
			end
			return true
		end,
		{
			"run",
			"python",
			"-m",
			"src.main",
			M.xmlPath,
			"--mode=websocket",
			"--ws-port=" .. M.port,
			"--no-signals",
		}
	)

	M.wsTask:setWorkingDirectory(projectRoot)
	local started = M.wsTask:start()

	if started then
		print("[WebSocket] Server started on port " .. M.port)
		return true
	else
		print("[WebSocket] ERROR: Failed to start server")
		return false
	end
end

-- Start file watcher for project file
function M.startFileWatcher(projectPath)
	M.stopFileWatcher()

	if not projectPath then
		return
	end

	-- Watch the project file for changes
	M.fileWatcher = hs.pathwatcher.new(projectPath, onFileChanged):start()
	print("[WebSocket] Watching file: " .. projectPath)
end

-- Stop file watcher
function M.stopFileWatcher()
	if M.fileWatcher then
		M.fileWatcher:stop()
		M.fileWatcher = nil
		print("[WebSocket] File watcher stopped")
	end
end

-- Stop WebSocket server
function M.stop()
	if M.wsTask then
		M.wsTask:terminate()
		M.wsTask = nil
	end

	-- Stop file watcher
	M.stopFileWatcher()

	-- Also kill any orphaned processes
	hs.execute("lsof -ti :" .. M.port .. " | xargs kill -9 2>/dev/null")

	print("[WebSocket] Server stopped")
end

-- Check if server is running
function M.isRunning()
	local output = hs.execute("lsof -ti :" .. M.port)
	return output and output:len() > 0
end

-- Restart server with current project
function M.restart()
	if M.projectPath then
		print("[WebSocket] Restarting server...")
		M.start(M.projectPath)
	else
		print("[WebSocket] Cannot restart: no project path stored")
	end
end

-- Get current status
function M.getStatus()
	return {
		running = M.isRunning(),
		port = M.port,
		projectPath = M.projectPath,
		xmlPath = M.xmlPath,
	}
end

return M
