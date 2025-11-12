local M = {}

M.timeout = {
	doubleTap = 0.2,
	sequence = 0.2,
}

-- Directories to watch for Ableton project (.als) file saves
-- The project watcher monitors these directories and auto-starts the WebSocket server
-- when you save a project (Cmd+S in Ableton)
M.projectWatchDirs = {
	os.getenv("HOME") .. "/Music", -- Default macOS Music folder
	os.getenv("HOME") .. "/Development/python/VimAbl/Example_Project",
	"/Volumes/ExterneSSD/Ableton Projekte", -- External SSD
	-- Add your custom project directories below:
	-- os.getenv("HOME") .. "/Documents/Ableton",
	-- "/Volumes/MyDrive/Projects",
}

return M
