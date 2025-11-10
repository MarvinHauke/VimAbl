-- Editing keybindings (delete, undo, etc.)
local utils = require("utils")

local M = {}

-- Keep references to eventtaps for monitoring
local ddTap = nil
local zaTap = nil
local monitorTimer = nil

function M.setup()
	-- Double-tap d for delete
	ddTap = utils.createDoubleTap(2, "Live", function()
		hs.eventtap.keyStroke({}, "delete")
	end)

	-- za - Undo
	zaTap = utils.createSequence({ "z", "a" }, "Live", function()
		hs.eventtap.keyStroke({}, "u")
	end)

	-- Monitor and restart eventtaps if they stop
	monitorTimer = hs.timer.doEvery(5, function()
		if ddTap and not ddTap:isEnabled() then
			print("Editing: WARNING - dd eventtap was disabled, restarting...")
			ddTap:start()
		end
		if zaTap and not zaTap:isEnabled() then
			print("Editing: WARNING - za eventtap was disabled, restarting...")
			zaTap:start()
		end
	end)

	print("Editing: Keybindings registered with monitoring")
end

function M.stop()
	if ddTap then
		ddTap:stop()
	end
	if zaTap then
		zaTap:stop()
	end
	if monitorTimer then
		monitorTimer:stop()
	end
end

return M
