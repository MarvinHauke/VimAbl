"""
Observer setup and callbacks for Live view changes and real-time UDP/OSC events

PERFORMANCE TUNING:
-------------------
Logging is controlled centrally in logging_config.py
Set ENABLE_LOGGING = False for better performance (~10-20% CPU reduction)

Critical errors will still be logged regardless of setting.
"""

import time

# Import centralized logging
from .logging_config import log


class ViewObservers:
    """Manages observers for Live's view changes"""

    def __init__(self, application, log_callback):
        """Initialize observers

        Args:
            application: Live.Application instance
            log_callback: Function to call for logging (e.g., self.log_message)
        """
        self.application = application
        self.log_message = log_callback

        # State tracking
        self.current_view = "session"  # Default to session view
        self.browser_visible = False
        self.device_visible = False
        self.clip_view_visible = False
        self.detail_view = "device"  # "device" or "clip"
        self.groove_pool_visible = False
        self.info_view_visible = False

    def setup(self):
        """Setup observers for view changes"""
        view = self.application.view

        # Add observers for view changes (with error handling for duplicates)
        self._add_observer(view, "Session", self._on_view_changed)
        self._add_observer(view, "Arranger", self._on_view_changed)
        self._add_observer(view, "Browser", self._on_browser_changed)
        self._add_observer(view, "Detail", self._on_device_changed)
        self._add_observer(view, "Detail/DeviceChain", self._on_device_changed)
        self._add_observer(view, "Detail/Clip", self._on_clip_changed)
        self._add_observer(view, "GroovePool", self._on_groove_pool_changed)
        self._add_observer(view, "Help", self._on_info_view_changed)

    def _add_observer(self, view, view_name, callback):
        """Add an observer with error handling for duplicates"""
        try:
            view.add_is_view_visible_listener(view_name, callback)
        except RuntimeError:
            pass  # Observer already connected

    def teardown(self):
        """Remove all observers"""
        view = self.application.view

        self._remove_observer(view, "Session", self._on_view_changed)
        self._remove_observer(view, "Arranger", self._on_view_changed)
        self._remove_observer(view, "Browser", self._on_browser_changed)
        self._remove_observer(view, "Detail", self._on_device_changed)
        self._remove_observer(view, "Detail/DeviceChain", self._on_device_changed)
        self._remove_observer(view, "Detail/Clip", self._on_clip_changed)
        self._remove_observer(view, "GroovePool", self._on_groove_pool_changed)
        self._remove_observer(view, "Help", self._on_info_view_changed)

    def _remove_observer(self, view, view_name, callback):
        """Remove an observer with error handling"""
        try:
            view.remove_is_view_visible_listener(view_name, callback)
        except RuntimeError:
            pass

    def _on_view_changed(self):
        """Called when view visibility changes"""
        view = self.application.view

        if view.is_view_visible("Arranger"):
            self.current_view = "arrangement"
            self.log_message("Switched to Arrangement view")
        elif view.is_view_visible("Session"):
            self.current_view = "session"
            self.log_message("Switched to Session view")

    def _on_browser_changed(self):
        """Called when browser visibility changes"""
        view = self.application.view
        self.browser_visible = view.is_view_visible("Browser")
        self.log_message(f"Browser visible: {self.browser_visible}")

    def _on_device_changed(self):
        """Called when device view visibility changes"""
        view = self.application.view
        self.device_visible = view.is_view_visible("Detail") or view.is_view_visible("Detail/DeviceChain")

        # Update which detail view is active
        if view.is_view_visible("Detail/DeviceChain"):
            self.detail_view = "device"

        self.log_message(f"Device view visible: {self.device_visible}, detail_view: {self.detail_view}")

    def _on_clip_changed(self):
        """Called when clip view visibility changes"""
        view = self.application.view
        self.clip_view_visible = view.is_view_visible("Detail/Clip")

        # Update which detail view is active
        if self.clip_view_visible:
            self.detail_view = "clip"

        self.log_message(f"Clip view visible: {self.clip_view_visible}, detail_view: {self.detail_view}")

    def _on_groove_pool_changed(self):
        """Called when groove pool visibility changes"""
        view = self.application.view
        self.groove_pool_visible = view.is_view_visible("GroovePool")
        self.log_message(f"Groove Pool visible: {self.groove_pool_visible}")

    def _on_info_view_changed(self):
        """Called when info view visibility changes"""
        view = self.application.view
        self.info_view_visible = view.is_view_visible("Help")
        self.log_message(f"Info View visible: {self.info_view_visible}")

    def get_state(self):
        """Get current state dictionary"""
        return {
            "view": self.current_view,
            "browser_visible": self.browser_visible,
            "device_visible": self.device_visible,
            "clip_view_visible": self.clip_view_visible,
            "detail_view": self.detail_view,
            "groove_pool_visible": self.groove_pool_visible,
            "info_view_visible": self.info_view_visible
        }


# ============================================================================
# UDP/OSC Real-Time Observers (for AST updates)
# ============================================================================


class Debouncer:
    """
    Debounces rapid events with "trailing edge" guarantee.

    Features:
    - Leading edge: Sends events at intervals during continuous changes (50-100ms)
    - Trailing edge: Always sends final value after user stops (150ms of silence)

    This ensures:
    - Smooth updates during fader movement (no flooding)
    - Final value is ALWAYS sent, even if user stops between intervals

    Example:
        User moves tempo fader: 91 -> 104 -> 106 -> 94 -> stops at 80 BPM
        - Leading edge sends: 91, 106 (at 50ms intervals during movement)
        - Trailing edge sends: 80 (150ms after user stops)
        Result: Final tempo is correct!
    """

    def __init__(self):
        """Initialize debouncer with empty state."""
        self.last_send_time = {}      # event_key -> timestamp of last send
        self.pending_values = {}      # event_key -> (value, callback, timestamp)
        self.trailing_timers = {}     # event_key -> scheduled trigger time

    def trigger(self, event_key, value, callback,
                min_interval_ms=50,
                trailing_ms=150):
        """
        Trigger a debounced event with trailing edge guarantee.

        Args:
            event_key: Unique key for this event (e.g., "track.volume:0")
            value: The current value to potentially send
            callback: Function to call when sending: callback(value)
            min_interval_ms: Minimum interval between sends (leading edge)
            trailing_ms: Time to wait after last change before sending final value
        """
        now = time.time()

        # Store this as the potentially final value
        self.pending_values[event_key] = (value, callback, now)

        # Leading edge: Send immediately if enough time passed
        last_send = self.last_send_time.get(event_key, 0)
        if (now - last_send) * 1000 >= min_interval_ms:
            callback(value)
            self.last_send_time[event_key] = now
            # Clear pending since we just sent it
            if event_key in self.pending_values:
                del self.pending_values[event_key]

        # Schedule trailing edge: Send final value after silence
        self.trailing_timers[event_key] = now + (trailing_ms / 1000.0)

    def check_trailing_edge(self):
        """
        Check and send any pending trailing edge values.

        Should be called periodically (e.g., every 50-100ms) by the observer manager.
        This is typically called from the RemoteScript's update_display() method.
        """
        # Early exit if no pending timers (performance optimization)
        if not self.trailing_timers:
            return

        now = time.time()
        keys_to_remove = []

        for event_key, trigger_time in list(self.trailing_timers.items()):
            if now >= trigger_time:
                # Time to send the trailing edge!
                if event_key in self.pending_values:
                    value, callback, pending_time = self.pending_values[event_key]

                    # Only send if this is still the latest value
                    # (check that no newer value was triggered)
                    if pending_time + (150 / 1000.0) <= now:
                        try:
                            callback(value)
                            self.last_send_time[event_key] = now
                        except Exception as e:
                            print("[Debouncer] Error sending trailing edge: " + str(e))

                        if event_key in self.pending_values:
                            del self.pending_values[event_key]

                keys_to_remove.append(event_key)

        # Clean up processed timers
        for key in keys_to_remove:
            del self.trailing_timers[key]

    def should_send(self, event_key, min_interval_ms):
        """
        Legacy method for backward compatibility.

        WARNING: This method does NOT provide trailing edge guarantee.
        Consider migrating to trigger() for continuous parameters.

        Args:
            event_key: Unique key for this event type (e.g., "track.volume:0")
            min_interval_ms: Minimum interval in milliseconds

        Returns:
            bool: True if event should be sent, False if too soon
        """
        now = time.time()
        last = self.last_send_time.get(event_key, 0)

        if (now - last) * 1000 >= min_interval_ms:
            self.last_send_time[event_key] = now
            return True
        else:
            return False


class TrackObserver:
    """
    Observes changes to a single track for UDP/OSC events.

    Monitors: name, mute, arm, volume, devices list
    """

    def __init__(self, track, track_index: int, udp_sender, debouncer):
        """
        Initialize track observer.

        Args:
            track: Live.Track.Track object
            track_index: Index of this track in the song
            udp_sender: UDPSender instance
            debouncer: Debouncer instance
        """
        self.track = track
        self.track_index = track_index
        self.sender = udp_sender
        self.debouncer = debouncer
        self.device_observers = []
        self.clip_slot_states = {}  # (track_idx, scene_idx) -> has_clip state
        self.clip_slot_callbacks = {}  # scene_idx -> callback function

        # Register listeners
        try:
            # Name listener
            if track.name_has_listener(self._on_name_changed):
                track.remove_name_listener(self._on_name_changed)
            track.add_name_listener(self._on_name_changed)

            # Mute listener
            if track.mute_has_listener(self._on_mute_changed):
                track.remove_mute_listener(self._on_mute_changed)
            track.add_mute_listener(self._on_mute_changed)

            # Arm listener (only for armable tracks)
            if hasattr(track, 'can_be_armed') and track.can_be_armed:
                if track.arm_has_listener(self._on_arm_changed):
                    track.remove_arm_listener(self._on_arm_changed)
                track.add_arm_listener(self._on_arm_changed)

            # Mixer device for volume
            if track.mixer_device:
                self._observe_volume(track.mixer_device)

            # Device list
            if track.devices_has_listener(self._on_devices_changed):
                track.remove_devices_listener(self._on_devices_changed)
            track.add_devices_listener(self._on_devices_changed)

            # Observe initial devices
            self._observe_devices()

            # Clip slots listener
            if track.clip_slots_has_listener(self._on_clip_slots_changed):
                track.remove_clip_slots_listener(self._on_clip_slots_changed)
            track.add_clip_slots_listener(self._on_clip_slots_changed)

            # Observe initial clip slots
            num_slots = len(track.clip_slots) if track.clip_slots else 0
            self._observe_clip_slots()

            # Log summary
            self.log(f"Track {track_index}: Initialized ({num_slots} clip slots)")

        except Exception as e:
            self.log(f"Track {track_index}: ERROR in __init__: {e}", force=True)

    def _observe_volume(self, mixer_device):
        """Observe volume parameter of mixer device."""
        try:
            volume_param = mixer_device.volume
            if volume_param.value_has_listener(self._on_volume_changed):
                volume_param.remove_value_listener(self._on_volume_changed)
            volume_param.add_value_listener(self._on_volume_changed)
        except Exception as e:
            self.log(f"Error observing volume: {e}")

    def _observe_devices(self):
        """Set up observers for all devices on this track."""
        # Clear old observers
        for obs in self.device_observers:
            obs.unregister()
        self.device_observers = []

        # Create new observers
        try:
            for device_idx, device in enumerate(self.track.devices):
                obs = DeviceObserver(device, self.track_index, device_idx,
                                    self.sender, self.debouncer)
                self.device_observers.append(obs)
        except Exception as e:
            self.log(f"Error observing devices: {e}")

    def _on_name_changed(self):
        """Called when track name changes."""
        try:
            name = str(self.track.name)
            self.sender.send_event("/live/track/renamed", self.track_index, name)
            self.log(f"Track {self.track_index} renamed to '{name}'")
        except Exception as e:
            self.log(f"Error handling name change: {e}")

    def _on_mute_changed(self):
        """Called when track mute state changes."""
        try:
            muted = bool(self.track.mute)
            self.sender.send_event("/live/track/mute", self.track_index, muted)
            self.log(f"Track {self.track_index} mute: {muted}")
        except Exception as e:
            self.log(f"Error handling mute change: {e}")

    def _on_arm_changed(self):
        """Called when track arm state changes."""
        try:
            armed = bool(self.track.arm)
            self.sender.send_event("/live/track/arm", self.track_index, armed)
            self.log(f"Track {self.track_index} arm: {armed}")
        except Exception as e:
            self.log(f"Error handling arm change: {e}")

    def _on_volume_changed(self):
        """Called when track volume changes (debounced with trailing edge)."""
        try:
            volume = float(self.track.mixer_device.volume.value)
            event_key = "track.volume:" + str(self.track_index)

            # Use new trigger() method for trailing edge guarantee
            def send_volume(vol):
                self.sender.send_event("/live/track/volume", self.track_index, vol)

            self.debouncer.trigger(event_key, volume, send_volume,
                                  min_interval_ms=50, trailing_ms=150)
            # Don't log every volume change (too noisy)
        except Exception as e:
            self.log("Error handling volume change: " + str(e))

    def _on_devices_changed(self):
        """Called when devices are added/removed from track."""
        try:
            self.log(f"Track {self.track_index} devices changed")
            # Re-observe all devices
            self._observe_devices()

            # Send device list update (could be add or remove)
            # For now, just log - full resync will happen via XML
            # TODO: Detect specific add/remove and send targeted events
        except Exception as e:
            self.log(f"Error handling devices change: {e}")

    def _observe_clip_slots(self):
        """Set up listeners for all clip slots on this track."""
        try:
            for scene_idx, clip_slot in enumerate(self.track.clip_slots):
                # Store initial state
                has_clip = clip_slot.has_clip
                self.clip_slot_states[(self.track_index, scene_idx)] = {
                    'has_clip': has_clip,
                    'has_stop_button': clip_slot.has_stop_button,
                    'playing_status': clip_slot.playing_status,
                    'color': clip_slot.color if hasattr(clip_slot, 'color') else None
                }

                # Create callbacks for this slot
                if scene_idx not in self.clip_slot_callbacks:
                    self.clip_slot_callbacks[scene_idx] = {
                        'has_clip': self._create_has_clip_callback(scene_idx),
                        'has_stop_button': self._create_has_stop_callback(scene_idx),
                        'playing_status': self._create_playing_status_callback(scene_idx),
                        'color': self._create_color_callback(scene_idx)
                    }

                callbacks = self.clip_slot_callbacks[scene_idx]

                # Add ClipSlot listeners
                if clip_slot.has_clip_has_listener(callbacks['has_clip']):
                    clip_slot.remove_has_clip_listener(callbacks['has_clip'])
                clip_slot.add_has_clip_listener(callbacks['has_clip'])

                if clip_slot.has_stop_button_has_listener(callbacks['has_stop_button']):
                    clip_slot.remove_has_stop_button_listener(callbacks['has_stop_button'])
                clip_slot.add_has_stop_button_listener(callbacks['has_stop_button'])

                if clip_slot.playing_status_has_listener(callbacks['playing_status']):
                    clip_slot.remove_playing_status_listener(callbacks['playing_status'])
                clip_slot.add_playing_status_listener(callbacks['playing_status'])

                if hasattr(clip_slot, 'color') and clip_slot.color_has_listener(callbacks['color']):
                    clip_slot.remove_color_listener(callbacks['color'])
                if hasattr(clip_slot, 'color'):
                    clip_slot.add_color_listener(callbacks['color'])

                # If slot has a clip, observe clip properties
                if has_clip and clip_slot.clip:
                    self._observe_clip(clip_slot.clip, scene_idx)

            self.log(f"Track {self.track_index}: Observing {len(self.track.clip_slots)} clip slots")
        except Exception as e:
            self.log(f"Error observing clip slots: {e}")

    def _create_clip_slot_callback(self, scene_idx):
        """Create a callback for a specific clip slot's has_clip listener."""
        def callback():
            self._on_clip_slot_changed(scene_idx)
        return callback

    def _create_has_clip_callback(self, scene_idx):
        """Create a callback for has_clip listener."""
        def callback():
            self._on_clip_slot_changed(scene_idx)
        return callback

    def _create_has_stop_callback(self, scene_idx):
        """Create a callback for has_stop_button listener."""
        def callback():
            self._on_has_stop_changed(scene_idx)
        return callback

    def _create_playing_status_callback(self, scene_idx):
        """Create a callback for playing_status listener."""
        def callback():
            self._on_playing_status_changed(scene_idx)
        return callback

    def _create_color_callback(self, scene_idx):
        """Create a callback for color listener."""
        def callback():
            self._on_slot_color_changed(scene_idx)
        return callback

    def _observe_clip(self, clip, scene_idx):
        """Observe properties of a Clip object."""
        try:
            # Store clip callbacks for cleanup
            if not hasattr(self, 'clip_callbacks'):
                self.clip_callbacks = {}

            clip_callbacks = {
                'name': lambda: self._on_clip_name_changed(scene_idx),
                'color': lambda: self._on_clip_color_changed(scene_idx),
                'muted': lambda: self._on_clip_muted_changed(scene_idx),
                'looping': lambda: self._on_clip_looping_changed(scene_idx),
            }

            self.clip_callbacks[scene_idx] = clip_callbacks

            # Add Clip listeners
            if clip.name_has_listener(clip_callbacks['name']):
                clip.remove_name_listener(clip_callbacks['name'])
            clip.add_name_listener(clip_callbacks['name'])

            if clip.color_has_listener(clip_callbacks['color']):
                clip.remove_color_listener(clip_callbacks['color'])
            clip.add_color_listener(clip_callbacks['color'])

            if clip.muted_has_listener(clip_callbacks['muted']):
                clip.remove_muted_listener(clip_callbacks['muted'])
            clip.add_muted_listener(clip_callbacks['muted'])

            if clip.looping_has_listener(clip_callbacks['looping']):
                clip.remove_looping_listener(clip_callbacks['looping'])
            clip.add_looping_listener(clip_callbacks['looping'])

        except Exception as e:
            self.log(f"Error observing clip at scene {scene_idx}: {e}")

    def _on_has_stop_changed(self, scene_idx):
        """Called when clip_slot has_stop_button changes."""
        try:
            clip_slot = self.track.clip_slots[scene_idx]
            has_stop = clip_slot.has_stop_button
            
            # Update state
            state = self.clip_slot_states.get((self.track_index, scene_idx), {})
            state['has_stop_button'] = has_stop
            self.clip_slot_states[(self.track_index, scene_idx)] = state

            self.sender.send_event("/live/clip_slot/has_stop",
                                  self.track_index, scene_idx, 1 if has_stop else 0)
            self.log(f"Clip slot [{self.track_index},{scene_idx}] has_stop: {has_stop}")
        except Exception as e:
            self.log(f"Error handling has_stop change at [{self.track_index},{scene_idx}]: {e}")

    def _on_playing_status_changed(self, scene_idx):
        """Called when clip_slot playback state changes."""
        try:
            clip_slot = self.track.clip_slots[scene_idx]
            status = clip_slot.playing_status
            
            # Update state
            state = self.clip_slot_states.get((self.track_index, scene_idx), {})
            state['playing_status'] = status
            self.clip_slot_states[(self.track_index, scene_idx)] = state

            self.sender.send_event("/live/clip_slot/playing_status",
                                  self.track_index, scene_idx, status)
            # Don't log every playing_status change (too noisy)
        except Exception as e:
            self.log(f"Error handling playing_status change at [{self.track_index},{scene_idx}]: {e}")

    def _on_slot_color_changed(self, scene_idx):
        """Called when clip_slot color changes."""
        try:
            clip_slot = self.track.clip_slots[scene_idx]
            color = clip_slot.color if hasattr(clip_slot, 'color') else None
            
            if color is not None:
                # Update state
                state = self.clip_slot_states.get((self.track_index, scene_idx), {})
                state['color'] = color
                self.clip_slot_states[(self.track_index, scene_idx)] = state

                self.sender.send_event("/live/clip_slot/color",
                                      self.track_index, scene_idx, color)
                self.log(f"Clip slot [{self.track_index},{scene_idx}] color: {color}")
        except Exception as e:
            self.log(f"Error handling slot color change at [{self.track_index},{scene_idx}]: {e}")

    def _on_clip_name_changed(self, scene_idx):
        """Called when clip name changes."""
        try:
            clip_slot = self.track.clip_slots[scene_idx]
            if clip_slot.has_clip and clip_slot.clip:
                name = str(clip_slot.clip.name)
                self.sender.send_event("/live/clip/name",
                                      self.track_index, scene_idx, name)
                self.log(f"Clip [{self.track_index},{scene_idx}] renamed: '{name}'")
        except Exception as e:
            self.log(f"Error handling clip name change at [{self.track_index},{scene_idx}]: {e}")

    def _on_clip_color_changed(self, scene_idx):
        """Called when clip color changes."""
        try:
            clip_slot = self.track.clip_slots[scene_idx]
            if clip_slot.has_clip and clip_slot.clip:
                color = clip_slot.clip.color
                self.sender.send_event("/live/clip/color",
                                      self.track_index, scene_idx, color)
                self.log(f"Clip [{self.track_index},{scene_idx}] color: {color}")
        except Exception as e:
            self.log(f"Error handling clip color change at [{self.track_index},{scene_idx}]: {e}")

    def _on_clip_muted_changed(self, scene_idx):
        """Called when clip muted state changes."""
        try:
            clip_slot = self.track.clip_slots[scene_idx]
            if clip_slot.has_clip and clip_slot.clip:
                muted = bool(clip_slot.clip.muted)
                self.sender.send_event("/live/clip/muted",
                                      self.track_index, scene_idx, 1 if muted else 0)
                self.log(f"Clip [{self.track_index},{scene_idx}] muted: {muted}")
        except Exception as e:
            self.log(f"Error handling clip muted change at [{self.track_index},{scene_idx}]: {e}")

    def _on_clip_looping_changed(self, scene_idx):
        """Called when clip looping state changes."""
        try:
            clip_slot = self.track.clip_slots[scene_idx]
            if clip_slot.has_clip and clip_slot.clip:
                looping = bool(clip_slot.clip.looping)
                self.sender.send_event("/live/clip/looping",
                                      self.track_index, scene_idx, 1 if looping else 0)
                self.log(f"Clip [{self.track_index},{scene_idx}] looping: {looping}")
        except Exception as e:
            self.log(f"Error handling clip looping change at [{self.track_index},{scene_idx}]: {e}")

    def _on_clip_slot_changed(self, scene_idx: int):
        """Called when a clip slot's has_clip state changes."""
        try:
            self.log(f"[DEBUG] _on_clip_slot_changed called for track {self.track_index}, scene {scene_idx}")

            clip_slot = self.track.clip_slots[scene_idx]
            has_clip = clip_slot.has_clip
            state = self.clip_slot_states.get((self.track_index, scene_idx), {})
            old_has_clip = state.get('has_clip', False)

            self.log(f"[DEBUG] has_clip={has_clip}, old_has_clip={old_has_clip}")

            # Update state
            state['has_clip'] = has_clip
            self.clip_slot_states[(self.track_index, scene_idx)] = state

            # Determine if clip was added or removed
            if has_clip and not old_has_clip:
                # Clip added
                clip_name = clip_slot.clip.name if clip_slot.clip else "Untitled"
                self.log(f"[DEBUG] Sending clip/added event: track={self.track_index}, scene={scene_idx}, name='{clip_name}'")
                self.sender.send_event("/live/clip/added", self.track_index, scene_idx, clip_name)
                self.log(f"Clip added at [{self.track_index},{scene_idx}]: '{clip_name}'")
                
                # Observe the newly added clip
                if clip_slot.clip:
                    self._observe_clip(clip_slot.clip, scene_idx)
            elif not has_clip and old_has_clip:
                # Clip removed
                self.log(f"[DEBUG] Sending clip/removed event: track={self.track_index}, scene={scene_idx}")
                self.sender.send_event("/live/clip/removed", self.track_index, scene_idx)
                self.log(f"Clip removed at [{self.track_index},{scene_idx}]")
                
                # Clean up clip listeners
                if hasattr(self, 'clip_callbacks') and scene_idx in self.clip_callbacks:
                    del self.clip_callbacks[scene_idx]
            else:
                self.log(f"[DEBUG] No state change detected (has_clip={has_clip}, old_has_clip={old_has_clip})")

        except Exception as e:
            self.log(f"Error handling clip slot change at [{self.track_index},{scene_idx}]: {e}")

    def _on_clip_slots_changed(self):
        """Called when the clip_slots list itself changes (scenes added/removed)."""
        try:
            self.log(f"Track {self.track_index} clip_slots list changed (scenes added/removed)")

            # Note: We do NOT send clip_slot/created events here anymore.
            # The ObserverManager handles scene additions (both insert and append)
            # and sends the corresponding clip_slot creation events with correct indices.
            # This prevents duplicate/incorrect events when inserting scenes.

            # Re-observe all clip slots (this will update stored states and re-attach listeners)
            self._observe_clip_slots()
        except Exception as e:
            self.log(f"Error handling clip_slots change: {e}")

    def unregister(self):
        """Unregister all listeners."""
        try:
            if self.track.name_has_listener(self._on_name_changed):
                self.track.remove_name_listener(self._on_name_changed)
            if self.track.mute_has_listener(self._on_mute_changed):
                self.track.remove_mute_listener(self._on_mute_changed)
            if self.track.arm_has_listener(self._on_arm_changed):
                self.track.remove_arm_listener(self._on_arm_changed)
            if self.track.devices_has_listener(self._on_devices_changed):
                self.track.remove_devices_listener(self._on_devices_changed)
            if self.track.clip_slots_has_listener(self._on_clip_slots_changed):
                self.track.remove_clip_slots_listener(self._on_clip_slots_changed)

            # Unregister volume listener
            if self.track.mixer_device:
                volume_param = self.track.mixer_device.volume
                if volume_param.value_has_listener(self._on_volume_changed):
                    volume_param.remove_value_listener(self._on_volume_changed)

            # Unregister clip slot listeners
            for scene_idx, clip_slot in enumerate(self.track.clip_slots):
                if scene_idx in self.clip_slot_callbacks:
                    callbacks = self.clip_slot_callbacks[scene_idx]
                    
                    # Remove ClipSlot listeners
                    if isinstance(callbacks, dict):
                        if clip_slot.has_clip_has_listener(callbacks['has_clip']):
                            clip_slot.remove_has_clip_listener(callbacks['has_clip'])
                        if clip_slot.has_stop_button_has_listener(callbacks['has_stop_button']):
                            clip_slot.remove_has_stop_button_listener(callbacks['has_stop_button'])
                        if clip_slot.playing_status_has_listener(callbacks['playing_status']):
                            clip_slot.remove_playing_status_listener(callbacks['playing_status'])
                        if hasattr(clip_slot, 'color') and clip_slot.color_has_listener(callbacks['color']):
                            clip_slot.remove_color_listener(callbacks['color'])
                    else:
                        # Old callback format (backwards compatibility)
                        if clip_slot.has_clip_has_listener(callbacks):
                            clip_slot.remove_has_clip_listener(callbacks)

                # Remove Clip listeners if they exist
                if hasattr(self, 'clip_callbacks') and scene_idx in self.clip_callbacks:
                    if clip_slot.has_clip and clip_slot.clip:
                        clip = clip_slot.clip
                        clip_callbacks = self.clip_callbacks[scene_idx]
                        
                        if clip.name_has_listener(clip_callbacks['name']):
                            clip.remove_name_listener(clip_callbacks['name'])
                        if clip.color_has_listener(clip_callbacks['color']):
                            clip.remove_color_listener(clip_callbacks['color'])
                        if clip.muted_has_listener(clip_callbacks['muted']):
                            clip.remove_muted_listener(clip_callbacks['muted'])
                        if clip.looping_has_listener(clip_callbacks['looping']):
                            clip.remove_looping_listener(clip_callbacks['looping'])

            self.clip_slot_callbacks.clear()
            if hasattr(self, 'clip_callbacks'):
                self.clip_callbacks.clear()

            # Unregister device observers
            for obs in self.device_observers:
                obs.unregister()
            self.device_observers = []

        except Exception as e:
            self.log(f"Error unregistering track observer: {e}")

    def log(self, message: str, force: bool = False):
        """
        Log message using centralized logging.

        Args:
            message: Message to log
            force: If True, log even if logging is disabled (for critical errors)
        """
        level = "ERROR" if force else "INFO"
        log("TrackObserver", message, level=level, force=force)


class DeviceObserver:
    """
    Observes changes to a single device for UDP/OSC events.

    Monitors: parameters (debounced)
    """

    def __init__(self, device, track_index: int, device_index: int,
                 udp_sender, debouncer):
        """
        Initialize device observer.

        Args:
            device: Live.Device.Device object
            track_index: Index of parent track
            device_index: Index of this device in track
            udp_sender: UDPSender instance
            debouncer: Debouncer instance
        """
        self.device = device
        self.track_index = track_index
        self.device_index = device_index
        self.sender = udp_sender
        self.debouncer = debouncer
        self.param_listeners = []

        # Observe parameters (limited - too many can be slow)
        try:
            # Only observe first 8 parameters (common controls)
            for param_idx, param in enumerate(list(device.parameters)[:8]):
                callback = lambda p=param, i=param_idx: self._on_param_changed(p, i)
                if param.value_has_listener(callback):
                    param.remove_value_listener(callback)
                param.add_value_listener(callback)
                self.param_listeners.append((param, param_idx, callback))
        except Exception as e:
            self.log(f"Error setting up device observer: {e}")

    def _on_param_changed(self, param, param_idx):
        """Called when device parameter changes (debounced with trailing edge)."""
        try:
            value = float(param.value)
            event_key = "device.param:" + str(self.track_index) + ":" + str(self.device_index) + ":" + str(param_idx)

            # Use new trigger() method for trailing edge guarantee
            def send_param(val):
                self.sender.send_event("/live/device/param",
                                      self.track_index,
                                      self.device_index,
                                      param_idx,
                                      val)

            self.debouncer.trigger(event_key, value, send_param,
                                  min_interval_ms=50, trailing_ms=150)
            # Don't log every param change (too noisy)
        except Exception as e:
            self.log("Error handling param change: " + str(e))

    def unregister(self):
        """Unregister all listeners."""
        try:
            for param, param_idx, callback in self.param_listeners:
                if param.value_has_listener(callback):
                    param.remove_value_listener(callback)
            self.param_listeners = []
        except Exception as e:
            self.log(f"Error unregistering device observer: {e}")

    def log(self, message: str, force: bool = False):
        """
        Log message using centralized logging.

        Args:
            message: Message to log
            force: If True, log even if logging is disabled (for critical errors)
        """
        level = "ERROR" if force else "INFO"
        log("DeviceObserver", message, level=level, force=force)


class TransportObserver:
    """
    Observes transport (playback) changes for UDP/OSC events.

    Monitors: is_playing, tempo
    """

    def __init__(self, song, udp_sender, debouncer):
        """
        Initialize transport observer.

        Args:
            song: Live.Song.Song object
            udp_sender: UDPSender instance
            debouncer: Debouncer instance
        """
        self.song = song
        self.sender = udp_sender
        self.debouncer = debouncer

        try:
            if song.is_playing_has_listener(self._on_playing_changed):
                song.remove_is_playing_listener(self._on_playing_changed)
            song.add_is_playing_listener(self._on_playing_changed)

            if song.tempo_has_listener(self._on_tempo_changed):
                song.remove_tempo_listener(self._on_tempo_changed)
            song.add_tempo_listener(self._on_tempo_changed)
        except Exception as e:
            self.log(f"Error setting up transport observer: {e}")

    def _on_playing_changed(self):
        """Called when playback starts/stops."""
        try:
            is_playing = bool(self.song.is_playing)
            self.sender.send_event("/live/transport/play", is_playing)
            self.log(f"Transport play: {is_playing}")
        except Exception as e:
            self.log(f"Error handling play change: {e}")

    def _on_tempo_changed(self):
        """Called when tempo changes (debounced with trailing edge)."""
        try:
            tempo = float(self.song.tempo)
            event_key = "transport.tempo"

            # Use new trigger() method for trailing edge guarantee
            def send_tempo(tmp):
                self.sender.send_event("/live/transport/tempo", tmp)
                self.log("Transport tempo: " + str(tmp))

            self.debouncer.trigger(event_key, tempo, send_tempo,
                                  min_interval_ms=100, trailing_ms=150)
        except Exception as e:
            self.log("Error handling tempo change: " + str(e))

    def unregister(self):
        """Unregister all listeners."""
        try:
            if self.song.is_playing_has_listener(self._on_playing_changed):
                self.song.remove_is_playing_listener(self._on_playing_changed)
            if self.song.tempo_has_listener(self._on_tempo_changed):
                self.song.remove_tempo_listener(self._on_tempo_changed)
        except Exception as e:
            self.log(f"Error unregistering transport observer: {e}")

    def log(self, message: str, force: bool = False):
        """
        Log message using centralized logging.

        Args:
            message: Message to log
            force: If True, log even if logging is disabled (for critical errors)
        """
        level = "ERROR" if force else "INFO"
        log("TransportObserver", message, level=level, force=force)


class SceneObserver:
    """
    Observes a single scene for name changes and triggered state.
    
    Sends UDP/OSC events:
    - /live/scene/renamed <scene_idx> <name>
    - /live/scene/triggered <scene_idx>
    - /live/scene/color <scene_idx> <color_rgb>
    """

    def __init__(self, scene, scene_index, udp_sender):
        """
        Initialize scene observer.

        Args:
            scene: Live.Scene.Scene object
            scene_index: Scene index (0-based)
            udp_sender: UDPSender instance
        """
        self.scene = scene
        self.scene_index = scene_index
        self.sender = udp_sender

        try:
            # Observe name changes
            if not scene.name_has_listener(self._on_name_changed):
                scene.add_name_listener(self._on_name_changed)

            # Observe color changes
            if hasattr(scene, 'color') and not scene.color_has_listener(self._on_color_changed):
                scene.add_color_listener(self._on_color_changed)

            # Observe triggered state
            if not scene.is_triggered_has_listener(self._on_triggered_changed):
                scene.add_is_triggered_listener(self._on_triggered_changed)

            self.log(f"Scene {scene_index}: Initialized (name='{scene.name}')")

        except Exception as e:
            self.log(f"Scene {scene_index}: ERROR in __init__: {e}", force=True)

    def _on_name_changed(self):
        """Called when scene name changes."""
        try:
            name = str(self.scene.name)
            self.sender.send_event("/live/scene/renamed", self.scene_index, name)
            self.log(f"Scene {self.scene_index} renamed: '{name}'")
        except Exception as e:
            self.log(f"Error handling scene name change: {e}", force=True)

    def _on_color_changed(self):
        """Called when scene color changes."""
        try:
            color_rgb = int(self.scene.color)
            self.sender.send_event("/live/scene/color", self.scene_index, color_rgb)
            self.log(f"Scene {self.scene_index} color changed: 0x{color_rgb:06X}")
        except Exception as e:
            self.log(f"Error handling scene color change: {e}", force=True)

    def _on_triggered_changed(self):
        """Called when scene is triggered."""
        try:
            is_triggered = bool(self.scene.is_triggered)
            if is_triggered:
                self.sender.send_event("/live/scene/triggered", self.scene_index)
                self.log(f"Scene {self.scene_index} triggered")
        except Exception as e:
            self.log(f"Error handling scene trigger: {e}", force=True)

    def unregister(self):
        """Unregister all listeners."""
        try:
            if self.scene.name_has_listener(self._on_name_changed):
                self.scene.remove_name_listener(self._on_name_changed)

            if hasattr(self.scene, 'color') and self.scene.color_has_listener(self._on_color_changed):
                self.scene.remove_color_listener(self._on_color_changed)

            if self.scene.is_triggered_has_listener(self._on_triggered_changed):
                self.scene.remove_is_triggered_listener(self._on_triggered_changed)

        except Exception as e:
            self.log(f"Error unregistering scene observer: {e}", force=True)

    def log(self, message: str, force: bool = False):
        """
        Log message using centralized logging.

        Args:
            message: Message to log
            force: If True, log even if logging is disabled (for critical errors)
        """
        level = "ERROR" if force else "INFO"
        log("SceneObserver", message, level=level, force=force)


class ObserverManager:
    """
    Manages all UDP/OSC observers for the current Live session.

    Handles registration, refresh, and cleanup of observers.
    """

    def __init__(self, song, udp_sender):
        """
        Initialize observer manager.

        Args:
            song: Live.Song.Song object
            udp_sender: UDPSender instance
        """
        log("ObserverManager", "Initializing...", level="INFO", force=True)
        
        self.song = song
        self.sender = udp_sender
        self.debouncer = Debouncer()

        self.track_observers = []
        self.scene_observers = []
        self.transport_observer = None
        self.enabled = False

        # Track scene count and objects for detecting add/remove/reorder
        self._scene_objects = list(song.scenes)
        self.scene_count = len(self._scene_objects)
        log("ObserverManager", f"Initial scene count: {self.scene_count}", level="INFO", force=True)

    def start(self):
        """Start observing all changes."""
        self.log("Starting observers...")
        self.enabled = True
        self._register_all_observers()
        self.log(f"Observers started: {len(self.track_observers)} tracks")

    def stop(self):
        """Stop observing all changes."""
        self.log("Stopping observers...")
        self.enabled = False
        self._unregister_all_observers()
        self.log("Observers stopped")

    def refresh(self):
        """Refresh observers (called when tracks change)."""
        if self.enabled:
            self.log("Refreshing observers...")
            self._unregister_all_observers()
            self._register_all_observers()
            self.log(f"Observers refreshed: {len(self.track_observers)} tracks")

    def _register_all_observers(self):
        """Register observers for all tracks, scenes, and transport."""
        try:
            # Transport observer
            self.transport_observer = TransportObserver(self.song, self.sender,
                                                       self.debouncer)
            self.log("[ObserverManager] Created TransportObserver")

            # Track observers
            track_count = 0
            for track_idx, track in enumerate(self.song.tracks):
                try:
                    obs = TrackObserver(track, track_idx, self.sender, self.debouncer)
                    self.track_observers.append(obs)
                    track_count += 1
                except Exception as track_err:
                    self.log(f"[ObserverManager] ERROR creating TrackObserver {track_idx}: {track_err}", force=True)

            self.log(f"[ObserverManager] Created {track_count} TrackObservers")

            # Scene observers
            scene_count = 0
            for scene_idx, scene in enumerate(self.song.scenes):
                try:
                    obs = SceneObserver(scene, scene_idx, self.sender)
                    self.scene_observers.append(obs)
                    scene_count += 1
                except Exception as scene_err:
                    self.log(f"[ObserverManager] ERROR creating SceneObserver {scene_idx}: {scene_err}", force=True)

            self.log(f"[ObserverManager] Created {scene_count} SceneObservers")

            # Listen for track list changes
            if self.song.tracks_has_listener(self._on_tracks_changed):
                self.song.remove_tracks_listener(self._on_tracks_changed)
            self.song.add_tracks_listener(self._on_tracks_changed)
            self.log("[ObserverManager] Added tracks_changed listener")

            # Listen for scene list changes
            if self.song.scenes_has_listener(self._on_scenes_changed):
                self.song.remove_scenes_listener(self._on_scenes_changed)
            self.song.add_scenes_listener(self._on_scenes_changed)
            self.log("[ObserverManager] Added scenes_changed listener")

        except Exception as e:
            self.log(f"Error registering observers: {e}", force=True)

    def _unregister_all_observers(self):
        """Unregister all observers."""
        try:
            # Transport observer
            if self.transport_observer:
                self.transport_observer.unregister()
                self.transport_observer = None

            # Track observers
            for obs in self.track_observers:
                obs.unregister()
            self.track_observers = []

            # Scene observers
            for obs in self.scene_observers:
                obs.unregister()
            self.scene_observers = []

            # Tracks listener
            if self.song.tracks_has_listener(self._on_tracks_changed):
                self.song.remove_tracks_listener(self._on_tracks_changed)

            # Scenes listener
            if self.song.scenes_has_listener(self._on_scenes_changed):
                self.song.remove_scenes_listener(self._on_scenes_changed)

        except Exception as e:
            self.log(f"Error unregistering observers: {e}")

    def _on_tracks_changed(self):
        """Called when tracks are added/removed."""
        self.log("Tracks list changed")
        self.refresh()

    def _on_scenes_changed(self):
        """Called when scenes are added/removed/reordered."""
        try:
            new_scenes = list(self.song.scenes)
            new_count = len(new_scenes)
            old_count = self.scene_count

            if new_count > old_count:
                # Scenes added
                added_count = new_count - old_count
                self.log(f"Scenes added: {added_count} (total: {new_count})")

                # Find insertion point by comparing object references
                # This handles both appending at end and inserting in middle
                insertion_indices = []

                if hasattr(self, '_scene_objects') and self._scene_objects:
                    old_scenes = self._scene_objects

                    # Find where new scenes were inserted by comparing object references
                    for new_idx, new_scene in enumerate(new_scenes):
                        # Check if this scene existed in old list
                        if new_scene not in old_scenes:
                            insertion_indices.append(new_idx)

                    # If scenes were inserted (not just appended), send reorder events
                    # for all scenes that got pushed down
                    min_insertion_idx = min(insertion_indices) if insertion_indices else old_count
                    if min_insertion_idx < old_count:
                        # Scenes were inserted in the middle, need to reorder everything after
                        # We iterate in reverse order (highest index first) to avoid collisions if we were doing local moves,
                        # but since we send absolute new indices, the order matters less for the final state,
                        # but matches Live's logic better.
                        # Note: Live API scenes list is already updated at this point.
                        for idx in range(min_insertion_idx, new_count):
                            if idx not in insertion_indices:
                                # This is an existing scene that got pushed down
                                scene = new_scenes[idx]
                                name = str(scene.name) if hasattr(scene, 'name') else f"Scene {idx + 1}"
                                self.sender.send_event("/live/scene/reordered", idx, name)
                                self.log(f"Scene {idx} reordered (pushed down): '{name}'")
                    
                    # Manually send clip_slot/created for new scenes across ALL tracks
                    # Done AFTER reordering to ensure slots at insertion indices are clear
                    for scene_idx in insertion_indices:
                        # Send scene/added event
                        scene = new_scenes[scene_idx]
                        name = str(scene.name) if hasattr(scene, 'name') else f"Scene {scene_idx + 1}"
                        self.sender.send_event("/live/scene/added", scene_idx, name)
                        self.log(f"Scene added: {scene_idx} '{name}'")

                        for track_idx, track in enumerate(self.song.tracks):
                            try:
                                if scene_idx < len(track.clip_slots):
                                    slot = track.clip_slots[scene_idx]
                                    # 0=stopped, 1=playing, 2=triggered
                                    status = slot.playing_status if hasattr(slot, 'playing_status') else 0
                                    
                                    self.sender.send_event("/live/clip_slot/created",
                                                         track_idx, scene_idx,
                                                         slot.has_clip, slot.has_stop_button,
                                                         status)
                            except Exception as e:
                                self.log(f"Error sending manual clip_slot create for track {track_idx}: {e}", force=True)
                else:
                    # Fallback: assume scenes added at end
                    for scene_idx in range(old_count, new_count):
                        scene = new_scenes[scene_idx]
                        name = str(scene.name) if hasattr(scene, 'name') else f"Scene {scene_idx + 1}"
                        self.sender.send_event("/live/scene/added", scene_idx, name)
                        self.log(f"Scene added: {scene_idx} '{name}'")
                        
                        # Manually send clip_slot/created for this new scene across ALL tracks
                        for track_idx, track in enumerate(self.song.tracks):
                            try:
                                if scene_idx < len(track.clip_slots):
                                    slot = track.clip_slots[scene_idx]
                                    status = slot.playing_status if hasattr(slot, 'playing_status') else 0
                                    
                                    self.sender.send_event("/live/clip_slot/created",
                                                         track_idx, scene_idx,
                                                         slot.has_clip, slot.has_stop_button,
                                                         status)
                            except Exception as e:
                                self.log(f"Error sending manual clip_slot create for track {track_idx}: {e}", force=True)

            elif new_count < old_count:
                # Scenes removed
                removed_count = old_count - new_count
                self.log(f"Scenes removed: {removed_count} (total: {new_count})")

                # Find which scenes were removed by comparing object references
                if hasattr(self, '_scene_objects'):
                    old_scenes = self._scene_objects
                    # Find removed scene indices
                    for old_idx, old_scene in enumerate(old_scenes):
                        if old_scene not in new_scenes:
                            self.sender.send_event("/live/scene/removed", old_idx)
                            self.log(f"Scene removed: {old_idx}")
                else:
                    # Fallback: send events for the last N scenes
                    for scene_idx in range(new_count, old_count):
                        self.sender.send_event("/live/scene/removed", scene_idx)
                        self.log(f"Scene removed: {scene_idx}")

            else:
                # Count unchanged - check for reordering
                # Compare scene object references to detect reordering
                if hasattr(self, '_scene_objects'):
                    old_scenes = self._scene_objects
                    # Check if any scene moved
                    reordered = False
                    for idx, scene in enumerate(new_scenes):
                        if idx < len(old_scenes) and scene != old_scenes[idx]:
                            reordered = True
                            break

                    if reordered:
                        self.log(f"Scenes reordered (total: {new_count})")
                        # Send reorder event with full scene list
                        scene_ids = []
                        for idx, scene in enumerate(new_scenes):
                            name = str(scene.name) if hasattr(scene, 'name') else f"Scene {idx + 1}"
                            scene_ids.append((idx, name))

                        # Send individual events for each scene's new position
                        for idx, name in scene_ids:
                            self.sender.send_event("/live/scene/reordered", idx, name)
                            self.log(f"Scene {idx} reordered: '{name}'")

            # Cache scene objects for reorder detection
            self._scene_objects = new_scenes

            # Update tracked count
            self.scene_count = new_count

            # Refresh all observers (will re-create scene observers)
            self.refresh()

        except Exception as e:
            self.log(f"Error in _on_scenes_changed: {e}", force=True)

    def update(self):
        """
        Update method - should be called periodically (e.g., from update_display()).

        Checks for:
        1. Trailing edge events from debouncer
        2. Scene count changes (Live API doesn't provide reliable listener!)
        """
        if self.enabled:
            self.debouncer.check_trailing_edge()
            
            # Poll for scene count changes (no reliable listener exists in Live API)
            try:
                new_count = len(list(self.song.scenes))
                
                # Debug: log every 60 polls (once per second at 60Hz)
                if not hasattr(self, '_poll_counter'):
                    self._poll_counter = 0
                self._poll_counter += 1
                
                if self._poll_counter % 60 == 0:
                    log("ObserverManager", f"Scene poll: {self.scene_count} vs {new_count}", level="INFO", force=True)

                if new_count != self.scene_count:
                    log("ObserverManager", f"Scene count changed: {self.scene_count} -> {new_count}", level="WARN", force=True)
                    self._on_scenes_changed()
            except Exception as e:
                log("ObserverManager", f"ERROR polling scene count: {e}", level="ERROR", force=True)

    def get_stats(self):
        """Get observer statistics."""
        return {
            "enabled": self.enabled,
            "track_count": len(self.track_observers),
            "scene_count": len(self.scene_observers),
            "has_transport": self.transport_observer is not None
        }

    def log(self, message, force: bool = False):
        """
        Log message using centralized logging.

        Args:
            message: Message to log
            force: If True, log even if logging is disabled (for critical errors)
        """
        level = "ERROR" if force else "INFO"
        log("ObserverManager", str(message), level=level, force=force)
