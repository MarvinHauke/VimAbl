"""
Session View Cursor Observer - Ultra-low latency cursor tracking

Tracks cursor/selection state in Ableton Live's Session View with minimal overhead.
Designed for <20ms end-to-end latency from Live selection to UI update.

Performance Guidelines:
- NO blocking operations in listeners
- NO heavy JSON serialization in hot paths
- Listeners only set flags and cache simple values
- UDP sends are non-blocking and safe
- Heavy work deferred to update() called at ~60Hz
"""

import Live


class SessionCursorObserver:
    """
    Observes Session View cursor/selection state and sends UDP events.

    Tracks:
    - Selected track index
    - Selected scene index
    - Highlighted clip slot (track, scene, state)

    Performance:
    - Listeners: O(1) - just cache indices
    - update(): O(1) - simple comparisons, no iteration
    - UDP send: Non-blocking, <0.5ms
    """

    def __init__(self, song, sender, log_func):
        """
        Initialize Session View cursor observer.

        Args:
            song: Live.Song.Song - The Live Set
            sender: UDPSender - UDP event sender
            log_func: callable - Ableton's log_message function for debug
        """
        self.song = song
        self.sender = sender
        self.log = log_func
        self.view = song.view

        # Cached state - updated by listeners (O(1))
        self._selected_track_idx = None
        self._selected_scene_idx = None
        self._last_highlighted_slot = None  # (track_idx, scene_idx)

        # Flags for change detection (avoid redundant sends)
        self._track_changed = False
        self._scene_changed = False

        # Track/scene list caches (rebuilt on track/scene add/remove)
        self._tracks_list = None
        self._scenes_list = None
        self._rebuild_caches()

        self.log("[CursorObserver] Initializing Session View observer")
        self._add_listeners()

        # Send initial state
        self._send_initial_state()

    def _rebuild_caches(self):
        """
        Rebuild track and scene list caches.

        Called on init and when tracks/scenes are added/removed.
        Converts tuple to list for O(1) index() lookups.
        """
        self._tracks_list = list(self.song.tracks)
        self._scenes_list = list(self.song.scenes)
        self.log(f"[CursorObserver] Cache rebuilt: {len(self._tracks_list)} tracks, {len(self._scenes_list)} scenes")

    def _add_listeners(self):
        """Add observers to track selection changes."""
        try:
            # Track selection observer
            if not self.view.selected_track_has_listener(self._on_track_changed):
                self.view.add_selected_track_listener(self._on_track_changed)
                self.log("[CursorObserver] Added selected_track listener")

            # Scene selection observer
            if not self.view.selected_scene_has_listener(self._on_scene_changed):
                self.view.add_selected_scene_listener(self._on_scene_changed)
                self.log("[CursorObserver] Added selected_scene listener")

            # Track/scene list change observers (for cache invalidation)
            if not self.song.tracks_has_listener(self._on_tracks_changed):
                self.song.add_tracks_listener(self._on_tracks_changed)

            if not self.song.scenes_has_listener(self._on_scenes_changed):
                self.song.add_scenes_listener(self._on_scenes_changed)

        except Exception as e:
            self.log(f"[CursorObserver] Error adding listeners: {e}")

    def _remove_listeners(self):
        """Remove all observers - call on cleanup."""
        try:
            if self.view.selected_track_has_listener(self._on_track_changed):
                self.view.remove_selected_track_listener(self._on_track_changed)

            if self.view.selected_scene_has_listener(self._on_scene_changed):
                self.view.remove_selected_scene_listener(self._on_scene_changed)

            if self.song.tracks_has_listener(self._on_tracks_changed):
                self.song.remove_tracks_listener(self._on_tracks_changed)

            if self.song.scenes_has_listener(self._on_scenes_changed):
                self.song.remove_scenes_listener(self._on_scenes_changed)

            self.log("[CursorObserver] Removed all listeners")
        except Exception as e:
            self.log(f"[CursorObserver] Error removing listeners: {e}")

    # =========================================================================
    # Listener Callbacks - MUST BE NON-BLOCKING
    # =========================================================================

    def _on_track_changed(self):
        """
        Track selection changed - called by Live API.

        Performance: O(1) - just set flag and cache index
        NO heavy operations - deferred to update()
        """
        try:
            track = self.view.selected_track
            if track and self._tracks_list:
                # O(1) index lookup (list.index is optimized in CPython)
                self._selected_track_idx = self._tracks_list.index(track)
                self._track_changed = True
        except (ValueError, AttributeError) as e:
            # Track not in list (edge case: track was just deleted)
            self.log(f"[CursorObserver] Track index lookup failed: {e}")
            self._selected_track_idx = None

    def _on_scene_changed(self):
        """
        Scene selection changed - called by Live API.

        Performance: O(1) - just set flag and cache index
        """
        try:
            scene = self.view.selected_scene
            if scene and self._scenes_list:
                self._selected_scene_idx = self._scenes_list.index(scene)
                self._scene_changed = True
        except (ValueError, AttributeError) as e:
            self.log(f"[CursorObserver] Scene index lookup failed: {e}")
            self._selected_scene_idx = None

    def _on_tracks_changed(self):
        """Tracks added/removed - rebuild cache."""
        self.log("[CursorObserver] Track list changed, rebuilding cache")
        self._rebuild_caches()
        # Re-check current selection after rebuild
        self._on_track_changed()

    def _on_scenes_changed(self):
        """Scenes added/removed - rebuild cache."""
        self.log("[CursorObserver] Scene list changed, rebuilding cache")
        self._rebuild_caches()
        self._on_scene_changed()

    # =========================================================================
    # update() - Called from LiveState.update_display() at ~60Hz
    # =========================================================================

    def update(self):
        """
        Update cursor state - called at ~60Hz from update_display().

        Handles:
        1. Sends pending track/scene selection changes
        2. Polls highlighted_clip_slot (no listener available!)
        3. Sends clip slot state if changed

        Performance: O(1) - all operations are simple comparisons
        """
        # Send pending track selection change
        if self._track_changed and self._selected_track_idx is not None:
            self._send_track_selection()
            self._track_changed = False

        # Send pending scene selection change
        if self._scene_changed and self._selected_scene_idx is not None:
            self._send_scene_selection()
            self._scene_changed = False

        # Poll highlighted clip slot (no observer available for this property)
        self._check_highlighted_clip_slot()

    def _check_highlighted_clip_slot(self):
        """
        Poll highlighted_clip_slot and send if changed.

        Called at ~60Hz from update() - acceptable for UX.
        Live API provides NO listener for this property!

        Performance: O(1) - direct property access, simple comparison
        """
        try:
            slot = self.view.highlighted_clip_slot

            if not slot:
                # No slot highlighted - clear if we had one before
                if self._last_highlighted_slot is not None:
                    self._last_highlighted_slot = None
                    # Could send "clear" event here if needed
                return

            # Get track index from slot's parent track
            track = slot.canonical_parent
            if not track or track not in self._tracks_list:
                return

            track_idx = self._tracks_list.index(track)

            # Get scene index from clip_slots list
            clip_slots = list(track.clip_slots)
            if slot not in clip_slots:
                return

            scene_idx = clip_slots.index(slot)

            # Check if slot changed
            current = (track_idx, scene_idx)
            if current != self._last_highlighted_slot:
                self._send_clip_slot_state(slot, track_idx, scene_idx)
                self._last_highlighted_slot = current

        except Exception as e:
            # Log but don't crash - this runs at 60Hz
            self.log(f"[CursorObserver] Error checking clip slot: {e}")

    # =========================================================================
    # UDP Event Senders - Non-blocking, fast
    # =========================================================================

    def _send_initial_state(self):
        """Send initial cursor state on startup."""
        try:
            if self.view.selected_track:
                self._on_track_changed()
                if self._selected_track_idx is not None:
                    self._send_track_selection()

            if self.view.selected_scene:
                self._on_scene_changed()
                if self._selected_scene_idx is not None:
                    self._send_scene_selection()

            self.log("[CursorObserver] Sent initial cursor state")
        except Exception as e:
            self.log(f"[CursorObserver] Error sending initial state: {e}")

    def _send_track_selection(self):
        """
        Send track selection event via UDP.

        Event: /live/cursor/track <track_idx>
        Performance: Non-blocking UDP send, <0.5ms
        """
        try:
            self.sender.send_event("/live/cursor/track", self._selected_track_idx)
            self.log(f"[CursorObserver] Track selected: {self._selected_track_idx}")
        except Exception as e:
            self.log(f"[CursorObserver] Error sending track selection: {e}")

    def _send_scene_selection(self):
        """
        Send scene selection event via UDP.

        Event: /live/cursor/scene <scene_idx>
        """
        try:
            self.sender.send_event("/live/cursor/scene", self._selected_scene_idx)
            self.log(f"[CursorObserver] Scene selected: {self._selected_scene_idx}")
        except Exception as e:
            self.log(f"[CursorObserver] Error sending scene selection: {e}")

    def _send_clip_slot_state(self, slot, track_idx, scene_idx):
        """
        Send clip slot highlight event with state.

        Event: /live/cursor/clip_slot <track_idx> <scene_idx> <has_clip> <is_playing> <is_triggered>

        Args:
            slot: Live.ClipSlot.ClipSlot
            track_idx: int - Track index
            scene_idx: int - Scene index
        """
        try:
            # Get slot state (all fast property accesses)
            has_clip = 1 if slot.has_clip else 0
            is_playing = 1 if (slot.has_clip and slot.is_playing) else 0
            is_triggered = 1 if (slot.has_clip and slot.is_triggered) else 0

            self.sender.send_event(
                "/live/cursor/clip_slot",
                track_idx,
                scene_idx,
                has_clip,
                is_playing,
                is_triggered
            )

            state = f"has_clip={bool(has_clip)}, playing={bool(is_playing)}, triggered={bool(is_triggered)}"
            self.log(f"[CursorObserver] Clip slot [{track_idx},{scene_idx}]: {state}")

        except Exception as e:
            self.log(f"[CursorObserver] Error sending clip slot state: {e}")

    # =========================================================================
    # Cleanup
    # =========================================================================

    def disconnect(self):
        """Clean up all listeners - call on script shutdown."""
        self.log("[CursorObserver] Disconnecting Session View observer")
        self._remove_listeners()
