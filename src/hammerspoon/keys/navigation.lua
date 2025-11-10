-- Navigation keybindings (gg, G for scrolling)
local liveState = require("live_state")
local utils = require("utils")

local M = {}

-- Keep references to eventtaps so we can monitor them
local gTap = nil
local ggTap = nil
local monitorTimer = nil

function M.setup()
	-- gg - Jump to start/first scene or track (auto-detects view)
	ggTap = utils.createSequence({ "g", "g" }, "Live", function()
		print("Navigation: gg triggered - jumping to first")
		liveState.jumpToFirst()
	end)

	-- G - Jump to end/last scene or track (auto-detects view)
	gTap = hs.eventtap.new({ hs.eventtap.event.types.keyDown }, function(event)
		local char = event:getCharacters()
		local frontApp = hs.application.frontmostApplication()

		if frontApp and frontApp:name() == "Live" and char == "G" then
			print("Navigation: G triggered - jumping to last")
			liveState.jumpToLast()
			return true
		end

		return false
	end)

	gTap:start()

	-- Monitor and restart eventtaps if they stop
	monitorTimer = hs.timer.doEvery(5, function()
		if gTap and not gTap:isEnabled() then
			print("Navigation: WARNING - G eventtap was disabled, restarting...")
			gTap:start()
		end
		if ggTap and not ggTap:isEnabled() then
			print("Navigation: WARNING - gg eventtap was disabled, restarting...")
			ggTap:start()
		end
	end)

	print("Navigation: G and gg bindings registered with monitoring")
end

function M.stop()
	if gTap then
		gTap:stop()
	end
	if monitorTimer then
		monitorTimer:stop()
	end
end

return M
