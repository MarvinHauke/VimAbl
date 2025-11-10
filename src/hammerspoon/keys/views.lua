-- View toggling keybindings (browser, etc.)
local M = {}

function M.setup()
	-- ctrl+- - Toggle browser
	hs.hotkey.bind({ "ctrl" }, "-", function()
		local frontApp = hs.application.frontmostApplication()

		if frontApp and frontApp:name() == "Live" then
			hs.eventtap.keyStroke({ "cmd", "alt" }, "b")
		end
	end)
end

return M
