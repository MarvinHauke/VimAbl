# Task Completion Checklist

When completing a coding task, follow these steps:

## 1. Code Validation

### Python Changes
- [ ] Check syntax: `python3 -m py_compile src/remote_script/LiveState.py`
- [ ] Verify no runtime errors by starting Ableton Live
- [ ] Check Ableton's log for errors: `tail -f ~/Library/Preferences/Ableton/Live\ */Log.txt`

### Lua Changes
- [ ] Check syntax if possible: `luac -p <file>.lua`
- [ ] Reload Hammerspoon config (Menu bar → Reload Config)
- [ ] Check Hammerspoon console for errors

## 2. Manual Testing

### For Python Remote Script Changes
- [ ] Restart Ableton Live to reload the Remote Script
- [ ] Verify Remote Script initialized: Check log for "Live State Remote Script initialized"
- [ ] Test socket commands: `echo "GET_VIEW" | nc 127.0.0.1 9001`
- [ ] Test new commands if added

### For Hammerspoon/Lua Changes
- [ ] Reload Hammerspoon config
- [ ] Test keybindings in Ableton Live
- [ ] Verify eventtaps are running (check console for warnings)

## 3. Integration Testing
- [ ] Test in both Session and Arrangement views (if context-aware)
- [ ] Verify keyboard shortcuts work as expected
- [ ] Check socket communication is working (20-50ms response time)
- [ ] Test auto-restart functionality for eventtaps (if applicable)

## 4. Documentation
- [ ] Update README.md if adding new commands or features
- [ ] Add command to command table in README if creating new socket command
- [ ] Document new keybindings in "Key Bindings" section

## 5. Git Workflow
- [ ] Review changes: `git status` and `git diff`
- [ ] Stage changes: `git add <files>`
- [ ] Commit with descriptive message: `git commit -m "feat: description"`
- [ ] Push if ready: `git push`

## 6. Cleanup
- [ ] Remove debug print statements (unless needed for troubleshooting)
- [ ] Check no temporary files were created
- [ ] Verify `.gitignore` is working correctly

## Notes
- **No automated tests** - rely on manual testing
- **No linters/formatters** - follow existing code style manually
- **Symlink setup** - changes reflect immediately after reload
- **Thread safety** - ensure new commands use `schedule_message()` for Live API calls
- **Error handling** - add try-except for observers and socket operations
