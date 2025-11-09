local config = require("config")
local M = {}

-- Double-Tap
local function createDoubleTap(keyCode, appName, action)
	local timer = nil

	local tap = hs.eventtap.new({ hs.eventtap.event.types.keyDown }, function(event)
		if event:getKeyCode() == keyCode then
			local frontApp = hs.application.frontmostApplication()

			if frontApp and frontApp:name() == appName then
				if timer then
					timer:stop()
					timer = nil
					action()
					return true
				else
					timer = hs.timer.doAfter(config.timeout.doubleTap, function()
						timer = nil
					end)
					return false
				end
			end
		end
		return false
	end)

	tap:start()
end

-- Key Sequence
local function createSequence(keys, appName, action)
	local sequence = {}
	local sequenceTimer = nil

	local tap = hs.eventtap.new({ hs.eventtap.event.types.keyDown }, function(event)
		local char = event:getCharacters()
		local frontApp = hs.application.frontmostApplication()

		if frontApp and frontApp:name() == appName and char then
			if sequenceTimer then
				sequenceTimer:stop()
			end

			table.insert(sequence, char)

			if #sequence == #keys then
				local match = true
				for i, key in ipairs(keys) do
					if sequence[i] ~= key then
						match = false
						break
					end
				end

				if match then
					action()
					sequence = {}
					return true
				end
				sequence = {}
			else
				sequenceTimer = hs.timer.doAfter(config.timeout.sequence, function()
					sequence = {}
				end)
			end
		end

		return false
	end)

	tap:start()
end

-- Shortcuts
createDoubleTap(2, "Live", function()
	hs.eventtap.keyStroke({}, "delete")
end)

hs.hotkey.bind({ "ctrl" }, "-", function()
	local frontApp = hs.application.frontmostApplication()
	if frontApp and frontApp:name() == "Live" then
		hs.eventtap.keyStroke({ "cmd", "alt" }, "b")
	end
end)

createSequence({ "z", "a" }, "Live", function()
	hs.eventtap.keyStroke({ "cmd", "alt" }, "u")
end)

return M
