-- WebSocket server manager for VimAbl TreeViewer
local M = {}

M.wsTask = nil
M.port = 8765
M.projectPath = nil

-- Start WebSocket server for a project
function M.start(projectPath)
	M.stop() -- Stop any existing server

	if not projectPath then
		print("[WebSocket] No project path provided")
		return false
	end

	M.projectPath = projectPath

	-- Find uv executable
	local uvPath = hs.execute("which uv"):gsub("%s+", "")
	if uvPath == "" then
		print("[WebSocket] ERROR: uv not found in PATH")
		return false
	end

	local projectRoot = os.getenv("HOME") .. "/Development/python/VimAbl"

	print("[WebSocket] Starting server for: " .. projectPath)

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
			projectPath,
			"--mode=websocket",
			"--ws-port=" .. M.port,
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

-- Stop WebSocket server
function M.stop()
	if M.wsTask then
		M.wsTask:terminate()
		M.wsTask = nil
	end

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
	}
end

return M
