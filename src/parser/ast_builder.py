from .file_refs import extract_file_refs
from .tracks import extract_tracks
from .devices import extract_devices
from .clips import extract_clips


def build_ast(root):
    """
    Build a comprehensive AST from the XML root.

    Args:
        root: XML root element

    Returns:
        Dictionary with tracks, file_refs, and enriched track data
    """
    # Extract basic track information
    tracks = extract_tracks(root)

    # Find all track elements in the XML
    track_elements = root.findall('.//Tracks/*')

    # Enrich each track with devices and clips
    for i, track_elem in enumerate(track_elements):
        if i < len(tracks):  # Make sure we don't go out of bounds
            # Extract devices for this track
            devices = extract_devices(track_elem)
            tracks[i]['devices'] = devices

            # Extract clips for this track
            clips = extract_clips(track_elem)
            tracks[i]['clips'] = clips

    return {
        "tracks": tracks,
        "file_refs": extract_file_refs(root),
    }
