from .file_refs import extract_file_refs
from .tracks import extract_tracks
from .devices import extract_devices
from .clips import extract_clips, extract_clip_slots
from .scenes import extract_scenes
from .mixer import extract_mixer_from_track


def build_ast(root):
    """
    Build a comprehensive AST from the XML root.

    Args:
        root: XML root element

    Returns:
        Dictionary with tracks, scenes, file_refs, and enriched track data
    """
    # Extract scenes FIRST to get the total number of scenes
    scenes = extract_scenes(root)
    num_scenes = len(scenes)

    # Extract basic track information (includes regular and return tracks from <Tracks>, plus master)
    tracks = extract_tracks(root)

    # Find all track elements in the XML (including return tracks)
    track_elements = root.findall('.//Tracks/*')
    master_track_element = root.find('.//MasterTrack')

    # Enrich each track with devices, clips, and mixer settings
    # Note: Return tracks (identified by type="return") won't have clips
    for i, track_elem in enumerate(track_elements):
        if i < len(tracks):  # Make sure we don't go out of bounds
            # Extract devices for this track
            devices = extract_devices(track_elem)
            tracks[i]['devices'] = devices

            # Extract clip slots and clips only for non-return tracks
            if tracks[i]['type'] != 'return':
                # Extract clip slots (all slots: empty and filled)
                # Pass num_scenes to ensure we get all slots, even empty ones
                clip_slots = extract_clip_slots(track_elem, num_scenes)
                tracks[i]['clip_slots'] = clip_slots

                # Also keep legacy clips array for backward compatibility (for now)
                clips = extract_clips(track_elem)
                tracks[i]['clips'] = clips

            # Extract mixer settings for this track
            mixer = extract_mixer_from_track(track_elem)
            tracks[i]['mixer'] = mixer

    # Enrich master track (if exists, it's always the last track in the list)
    if master_track_element is not None:
        master_idx = len(track_elements)  # Master is after all tracks in <Tracks>
        if master_idx < len(tracks):
            devices = extract_devices(master_track_element)
            tracks[master_idx]['devices'] = devices

            mixer = extract_mixer_from_track(master_track_element)
            tracks[master_idx]['mixer'] = mixer
            # Master track doesn't have clips

    return {
        "tracks": tracks,
        "scenes": scenes,
        "file_refs": extract_file_refs(root),
    }
