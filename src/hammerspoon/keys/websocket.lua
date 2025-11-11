-- WebSocket server keybindings for VimAbl TreeViewer
local wsManager = require("websocket_manager")
local projectWatcher = require("project_watcher")

local M = {}

function M.setup()
	-- Cmd+Shift+W - Toggle WebSocket server
	hs.hotkey.bind({ "cmd", "shift" }, "W", function()
		if wsManager.isRunning() then
			wsManager.stop()
			hs.alert.show("WebSocket Server Stopped")
		else
			-- Check if we have detected a project path
			local projectPath = projectWatcher.lastDetectedProject or wsManager.projectPath
			if projectPath then
				local success = wsManager.start(projectPath)
				if success then
					hs.alert.show("WebSocket Server Started\nPort: " .. wsManager.port)
				else
					hs.alert.show("Failed to start WebSocket server")
				end
			else
				hs.alert.show("No project detected\nSave your project (Cmd+S) and try again!")
			end
		end
	end)

	-- Cmd+Shift+R - Restart WebSocket server
	hs.hotkey.bind({ "cmd", "shift" }, "R", function()
		if wsManager.projectPath then
			wsManager.restart()
			hs.alert.show("WebSocket Server Restarted")
		else
			hs.alert.show("No server to restart")
		end
	end)

	-- Cmd+Shift+I - Show WebSocket server info/status
	hs.hotkey.bind({ "cmd", "shift" }, "I", function()
		local status = wsManager.getStatus()
		local message = "WebSocket Server Status\n\n"
		message = message .. "Running: " .. (status.running and "Yes" or "No") .. "\n"
		message = message .. "Port: " .. status.port .. "\n"
		if status.projectPath then
			-- Show only filename, not full path
			local filename = status.projectPath:match("([^/]+)$")
			message = message .. "Project: " .. filename
		else
			message = message .. "Project: None"
		end

		hs.alert.show(message, 4)
	end)

	print("Ableton VimMode: WebSocket keybindings loaded")
	print("  Cmd+Shift+W: Toggle WebSocket server")
	print("  Cmd+Shift+R: Restart WebSocket server")
	print("  Cmd+Shift+I: Show server status")
end

return M
