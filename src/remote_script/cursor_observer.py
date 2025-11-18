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

PERFORMANCE TUNING:
-------------------
Logging is controlled centrally in logging_config.py
Set ENABLE_LOGGING = False for better performance
"""

import Live
from .logging_config import log


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
            log_func: callable - Ableton's log_message function (DEPRECATED, uses centralized logging)
        """
        self.song = song
        self.sender = sender
        # Keep log_func for backward compatibility but not used
        self.view = song.view

        # Cached state - updated by listeners (O(1))
        self._selected_track_idx = None
        self._selected_track = None  # Cache track object for color/name
        self._selected_scene_idx = None
        self._last_highlighted_slot = None  # (track_idx, scene_idx)

        # Flags for change detection (avoid redundant sends)
        self._track_changed = False
        self._scene_changed = False
        self._color_changed = False  # Flag for color changes

        # Track/scene list caches (rebuilt on track/scene add/remove)
        self._tracks_list = None
        self._return_tracks_list = None
        self._master_track = None
        self._scenes_list = None
        self._rebuild_caches()

        log("CursorObserver", "Initializing Session View observer")
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
        self._return_tracks_list = list(self.song.return_tracks)
        self._master_track = self.song.master_track
        self._scenes_list = list(self.song.scenes)

        log("CursorObserver",
            f"Cache rebuilt: {len(self._tracks_list)} tracks, "
            f"{len(self._return_tracks_list)} returns, "
            f"{len(self._scenes_list)} scenes"
        )

    def _add_listeners(self):
        """Add observers to track selection changes."""
        try:
            # Track selection observer
            if not self.view.selected_track_has_listener(self._on_track_changed):
                self.view.add_selected_track_listener(self._on_track_changed)
                log("CursorObserver", "Added selected_track listener")

            # Scene selection observer
            if not self.view.selected_scene_has_listener(self._on_scene_changed):
                self.view.add_selected_scene_listener(self._on_scene_changed)
                log("CursorObserver", "Added selected_scene listener")

            # Track/scene list change observers (for cache invalidation)
            if not self.song.tracks_has_listener(self._on_tracks_changed):
                self.song.add_tracks_listener(self._on_tracks_changed)

            if not self.song.scenes_has_listener(self._on_scenes_changed):
                self.song.add_scenes_listener(self._on_scenes_changed)

        except Exception as e:
            log("CursorObserver", f"Error adding listeners: {e}")

    def _remove_listeners(self):
        """Remove all observers - call on cleanup."""
        try:
            # Remove color listener from selected track
            if self._selected_track and self._selected_track.color_has_listener(self._on_track_color_changed):
                self._selected_track.remove_color_listener(self._on_track_color_changed)
            
            if self.view.selected_track_has_listener(self._on_track_changed):
                self.view.remove_selected_track_listener(self._on_track_changed)

            if self.view.selected_scene_has_listener(self._on_scene_changed):
                self.view.remove_selected_scene_listener(self._on_scene_changed)

            if self.song.tracks_has_listener(self._on_tracks_changed):
                self.song.remove_tracks_listener(self._on_tracks_changed)

            if self.song.scenes_has_listener(self._on_scenes_changed):
                self.song.remove_scenes_listener(self._on_scenes_changed)

            log("CursorObserver", "Removed all listeners")
        except Exception as e:
            log("CursorObserver", f"Error removing listeners: {e}")

    # =========================================================================
    # Listener Callbacks - MUST BE NON-BLOCKING
    # =========================================================================

    def _on_track_changed(self):
        """
        Track selection changed - called by Live API.

        Performance: O(1) - just set flag and cache track reference
        Also adds color listener to the newly selected track.
        Handles regular tracks, return tracks, and master track.
        """
        try:
            # Remove color listener from old track
            if self._selected_track and self._selected_track.color_has_listener(self._on_track_color_changed):
                self._selected_track.remove_color_listener(self._on_track_color_changed)
            
            track = self.view.selected_track
            if not track:
                self._selected_track_idx = None
                self._selected_track = None
                return
            
            # Check master track FIRST (before return tracks)
            if track == self._master_track:
                # Master is always last
                self._selected_track_idx = len(self._tracks_list) + len(self._return_tracks_list)
                self._selected_track = track
                self._track_changed = True
                
                if not track.color_has_listener(self._on_track_color_changed):
                    track.add_color_listener(self._on_track_color_changed)
                
                log("CursorObserver", f"Master track selected, index: {self._selected_track_idx}")
                return
            
            # Try regular tracks
            try:
                if track in self._tracks_list:
                    self._selected_track_idx = self._tracks_list.index(track)
                    self._selected_track = track
                    self._track_changed = True
                    
                    # Add color listener to new track
                    if not track.color_has_listener(self._on_track_color_changed):
                        track.add_color_listener(self._on_track_color_changed)
                    return
            except ValueError:
                pass
            
            # Try return tracks
            try:
                if track in self._return_tracks_list:
                    # Return tracks start after regular tracks
                    return_idx = self._return_tracks_list.index(track)
                    self._selected_track_idx = len(self._tracks_list) + return_idx
                    self._selected_track = track
                    self._track_changed = True
                    
                    if not track.color_has_listener(self._on_track_color_changed):
                        track.add_color_listener(self._on_track_color_changed)
                    
                    log("CursorObserver", f"Return track selected: {return_idx}, global index: {self._selected_track_idx}")
                    return
            except ValueError:
                pass
            
            # Track not found in any list
            log("CursorObserver", f"Selected track not found in any track list")
            self._selected_track_idx = None
            self._selected_track = None
                    
        except (ValueError, AttributeError) as e:
            # Track not in list (edge case: track was just deleted)
            log("CursorObserver", f"Track index lookup failed: {e}")
            self._selected_track_idx = None
            self._selected_track = None

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
            log("CursorObserver", f"Scene index lookup failed: {e}")
            self._selected_scene_idx = None

    def _on_tracks_changed(self):
        """Tracks added/removed - rebuild cache."""
        log("CursorObserver", "Track list changed, rebuilding cache")
        self._rebuild_caches()
        # Re-check current selection after rebuild
        self._on_track_changed()

    def _on_scenes_changed(self):
        """Scenes added/removed - rebuild cache."""
        log("CursorObserver", "Scene list changed, rebuilding cache")
        self._rebuild_caches()
        self._on_scene_changed()

    def _on_track_color_changed(self):
        """
        Selected track's color changed - called by Live API.

        Performance: O(1) - just set flag
        """
        self._color_changed = True

    # =========================================================================
    # update() - Called from LiveState.update_display() at ~60Hz
    # =========================================================================

    def update(self):
        """
        Update cursor state - called at ~60Hz from update_display().

        Handles:
        1. Sends pending track/scene selection changes
        2. Sends track color changes
        3. Polls highlighted_clip_slot (no listener available!)
        4. Sends clip slot state if changed

        Performance: O(1) - all operations are simple comparisons
        """
        # Send pending track selection change
        if self._track_changed and self._selected_track_idx is not None:
            self._send_track_selection()
            self._track_changed = False

        # Send pending track color change (when user changes color in Live)
        if self._color_changed and self._selected_track_idx is not None:
            self._send_track_color_update()
            self._color_changed = False

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
            log("CursorObserver", f"Error checking clip slot: {e}")

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

            log("CursorObserver", "Sent initial cursor state")
        except Exception as e:
            log("CursorObserver", f"Error sending initial state: {e}")

    def _send_track_selection(self):
        """
        Send track selection event via UDP.

        Event: /live/cursor/track <track_idx> <color_rgb> <track_name>
        
        Sends actual RGB color from track.color (not color_index) so the
        WebUI displays the exact color from Ableton, not a hardcoded palette.
        
        Performance: Non-blocking UDP send, <0.5ms
        """
        try:
            track_idx = self._selected_track_idx
            
            # Get actual RGB color from Live API (format: 0xRRGGBB)
            color_rgb = None
            track_name = None
            
            if self._selected_track:
                # track.color returns actual RGB value used by Ableton
                # This is more accurate than using color_index with a palette
                try:
                    color_rgb = int(self._selected_track.color)
                except (AttributeError, ValueError):
                    color_rgb = None
                
                # Get track name
                try:
                    track_name = str(self._selected_track.name)
                except AttributeError:
                    track_name = None
            
            # Send with color and name
            if color_rgb is not None and track_name is not None:
                self.sender.send_event("/live/cursor/track", track_idx, color_rgb, track_name)
                log("CursorObserver", f"Track selected: {track_idx} '{track_name}' (0x{color_rgb:06X})")
            elif color_rgb is not None:
                self.sender.send_event("/live/cursor/track", track_idx, color_rgb)
                log("CursorObserver", f"Track selected: {track_idx} (0x{color_rgb:06X})")
            else:
                self.sender.send_event("/live/cursor/track", track_idx)
                log("CursorObserver", f"Track selected: {track_idx}")
                
        except Exception as e:
            log("CursorObserver", f"Error sending track selection: {e}")

    def _send_track_color_update(self):
        """
        Send track color update event via UDP.

        Event: /live/track/color <track_idx> <color_rgb>
        
        Sent when user changes a track's color in Live.
        Performance: Non-blocking UDP send, <0.5ms
        """
        try:
            if not self._selected_track:
                return
            
            track_idx = self._selected_track_idx
            
            # Get actual RGB color from Live API
            try:
                color_rgb = int(self._selected_track.color)
                self.sender.send_event("/live/track/color", track_idx, color_rgb)
                log("CursorObserver", f"Track {track_idx} color changed: 0x{color_rgb:06X}")
            except (AttributeError, ValueError) as e:
                log("CursorObserver", f"Error getting track color: {e}")
                
        except Exception as e:
            log("CursorObserver", f"Error sending track color update: {e}")

    def _send_scene_selection(self):
        """
        Send scene selection event via UDP.

        Event: /live/cursor/scene <scene_idx>
        """
        try:
            self.sender.send_event("/live/cursor/scene", self._selected_scene_idx)
            log("CursorObserver", f"Scene selected: {self._selected_scene_idx}")
        except Exception as e:
            log("CursorObserver", f"Error sending scene selection: {e}")

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
            log("CursorObserver", f"Clip slot [{track_idx},{scene_idx}]: {state}")

        except Exception as e:
            log("CursorObserver", f"Error sending clip slot state: {e}")

    # =========================================================================
    # Cleanup
    # =========================================================================

    def disconnect(self):
        """Clean up all listeners - call on script shutdown."""
        log("CursorObserver", "Disconnecting Session View observer")
        self._remove_listeners()
