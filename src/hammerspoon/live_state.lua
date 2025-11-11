local M = {}

M.HOST = "127.0.0.1"
M.PORT = 9001

-- Query the current view from the Remote Script using simpler approach
function M.getCurrentView()
	local handle = io.popen('echo "GET_VIEW" | nc -w 1 ' .. M.HOST .. " " .. M.PORT .. " 2>/dev/null")
	if not handle then
		return "session" -- Default fallback
	end

	local result = handle:read("*a")
	handle:close()

	if result and result ~= "" then
		local json = require("hs.json")
		local decoded = json.decode(result)
		if decoded and decoded.view then
			return decoded.view
		end
	end

	return "session" -- Default fallback
end

-- Get full state from Ableton
function M.getState()
	local handle = io.popen('echo "GET_STATE" | nc -w 1 ' .. M.HOST .. " " .. M.PORT .. " 2>/dev/null")
	if not handle then
		return nil
	end

	local result = handle:read("*a")
	handle:close()

	if result and result ~= "" then
		local json = require("hs.json")
		local decoded = json.decode(result)
		if decoded then
			return decoded
		end
	end

	return nil
end

-- Get current project path from Ableton
function M.getProjectPath()
	print("LiveState: Requesting project path from Ableton...")
	local handle = io.popen('echo "GET_PROJECT_PATH" | nc -w 1 ' .. M.HOST .. " " .. M.PORT .. " 2>/dev/null")
	if not handle then
		print("LiveState: ERROR - Failed to connect to Remote Script")
		return nil
	end

	local result = handle:read("*a")
	handle:close()

	if result and result ~= "" then
		local json = require("hs.json")
		local decoded = json.decode(result)
		if decoded and decoded.project_path then
			print("LiveState: Project path found: " .. decoded.project_path)
			return decoded.project_path
		else
			print("LiveState: No project path in response (project not saved)")
		end
	else
		print("LiveState: No response from Remote Script")
	end

	return nil
end

-- Export current project as XML to .vimabl directory
function M.exportXML(projectPath)
	local command
	if projectPath then
		-- Pass project path as colon-delimited parameter (protocol format: COMMAND:param1:param2)
		command = string.format('echo "EXPORT_XML:%s" | nc -w 2 %s %d 2>/dev/null', projectPath, M.HOST, M.PORT)
	else
		command = string.format('echo "EXPORT_XML" | nc -w 2 %s %d 2>/dev/null', M.HOST, M.PORT)
	end

	local handle = io.popen(command)
	if not handle then
		print("LiveState: Failed to send EXPORT_XML command")
		return nil, "Connection failed"
	end

	local result = handle:read("*a")
	handle:close()

	if result and result ~= "" then
		local json = require("hs.json")
		local decoded = json.decode(result)
		if decoded then
			if decoded.success then
				print("LiveState: XML export succeeded: " .. (decoded.xml_path or "unknown path"))
				return decoded.xml_path, nil
			else
				print("LiveState: XML export failed: " .. (decoded.error or "unknown error"))
				return nil, decoded.error
			end
		end
	end

	return nil, "No response from server"
end

-- Send command to Remote Script
local function sendCommand(command)
	print("LiveState: Sending command: " .. command)
	local handle = io.popen('echo "' .. command .. '" | nc -w 1 ' .. M.HOST .. " " .. M.PORT .. " 2>&1")
	if not handle then
		print("LiveState: ERROR - Failed to open connection")
		return false
	end

	local result = handle:read("*a")
	handle:close()

	print("LiveState: Received response: " .. (result or "nil"))

	if result and result ~= "" then
		local json = require("hs.json")
		local decoded = json.decode(result)
		if decoded then
			if decoded.success then
				print("LiveState: Command succeeded")
				return true
			else
				print("LiveState: Command failed: " .. (decoded.error or "unknown error"))
			end
		else
			print("LiveState: Failed to decode JSON")
		end
	else
		print("LiveState: No response from server")
	end

	return false
end

-- Scroll to top (Arrangement view)
function M.scrollToTop()
	return sendCommand("SCROLL_TO_TOP")
end

-- Scroll to bottom (Arrangement view)
function M.scrollToBottom()
	return sendCommand("SCROLL_TO_BOTTOM")
end

-- Jump to first (auto-detects view: first track in arrangement, first scene in session)
function M.jumpToFirst()
	return sendCommand("JUMP_TO_FIRST")
end

-- Jump to last (auto-detects view: last track in arrangement, last scene in session)
function M.jumpToLast()
	return sendCommand("JUMP_TO_LAST")
end

return M
