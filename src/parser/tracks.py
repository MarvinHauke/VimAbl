def extract_tracks(root):
    tracks = []
    
    # Extract all tracks from <Tracks> element
    # Return tracks are identified by tag name "ReturnTrack" within <Tracks>
    for i, track in enumerate(root.findall(".//Tracks/*")):
        # Extract track name from Value attribute (Ableton stores it there, not as text)
        name_elem = track.find(".//Name/EffectiveName")
        name = name_elem.get("Value", f"Track {i}") if name_elem is not None else f"Track {i}"

        # If name is empty, try UserName
        if not name or name.strip() == "":
            user_name_elem = track.find(".//Name/UserName")
            name = user_name_elem.get("Value", f"Track {i}") if user_name_elem is not None else f"Track {i}"

        # Extract color index (0-69 in Ableton's color palette)
        color_elem = track.find(".//Color")
        color_index = None
        if color_elem is not None:
            try:
                color_index = int(color_elem.get("Value", -1))
            except (ValueError, TypeError):
                color_index = None

        # Determine track type based on XML tag
        track_type = "return" if track.tag == "ReturnTrack" else "track"

        tracks.append({
            "index": i,
            "name": name,
            "color": color_index,
            "type": track_type
        })
    
    # Extract or create master track
    # The master track may be stored as <MasterTrack> element (newer versions)
    # or may not be in XML at all (older versions), but Live API always has one
    # Check both .//MasterTrack and root level MasterTrack
    master_track_elem = root.find(".//MasterTrack")
    if master_track_elem is None:
        master_track_elem = root.find("MasterTrack")

    master_track_index = len(tracks)  # Master track is always last

    if master_track_elem is not None:
        # Master track found in XML - extract name and color same as other tracks
        name_elem = master_track_elem.find(".//Name/EffectiveName")
        name = name_elem.get("Value", "Master") if name_elem is not None else "Master"

        if not name or name.strip() == "":
            user_name_elem = master_track_elem.find(".//Name/UserName")
            name = user_name_elem.get("Value", "Master") if user_name_elem is not None else "Master"

        color_elem = master_track_elem.find(".//Color")
        color_index = None
        if color_elem is not None:
            try:
                color_index = int(color_elem.get("Value", -1))
            except (ValueError, TypeError):
                color_index = None

        tracks.append({
            "index": master_track_index,
            "name": name,
            "color": color_index,
            "type": "master"
        })
    else:
        # No <MasterTrack> in XML, but Live API always has a master track
        # Create a placeholder entry so indices match Live API structure
        # Use generic "Master" name - will be updated by Live API events if needed
        tracks.append({
            "index": master_track_index,
            "name": "Main",
            "color": None,
            "type": "master"
        })
    
    return tracks
