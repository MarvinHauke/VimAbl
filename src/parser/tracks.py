def extract_tracks(root):
    tracks = []
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

        tracks.append({
            "index": i,
            "name": name,
            "color": color_index
        })
    return tracks
