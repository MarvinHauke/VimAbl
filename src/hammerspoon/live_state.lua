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
