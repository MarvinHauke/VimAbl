-- Navigation keybindings (gg, G for scrolling)
local liveState = require("live_state")
local utils = require("utils")

local M = {}

-- Keep references to eventtaps so we can monitor them
local gTap = nil
local ggTap = nil
local monitorTimer = nil

function M.setup()
	-- gg - Jump to start/first scene or track
	ggTap = utils.createSequence({ "g", "g" }, "Live", function()
		print("Navigation: gg triggered")
		local view = liveState.getCurrentView()
		print("Navigation: Current view = " .. tostring(view))

		if view == "arrangement" then
			print("Navigation: Selecting first track")
			liveState.selectFirstTrack()
		else
			-- Session view: Select first scene
			print("Navigation: Selecting first scene")
			liveState.selectFirstScene()
		end
	end)

	-- G - Jump to end/last scene
	gTap = hs.eventtap.new({ hs.eventtap.event.types.keyDown }, function(event)
		local char = event:getCharacters()
		local frontApp = hs.application.frontmostApplication()

		if frontApp and frontApp:name() == "Live" and char == "G" then
			print("Navigation: G triggered")
			local view = liveState.getCurrentView()
			print("Navigation: Current view = " .. tostring(view))

			if view == "arrangement" then
				print("Navigation: Selecting last track")
				liveState.selectLastTrack()
			else
				-- Session view: Select last scene
				print("Navigation: Selecting last scene")
				liveState.selectLastScene()
			end
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
