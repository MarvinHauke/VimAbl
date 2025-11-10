def extract_tracks(root):
    tracks = []
    for i, track in enumerate(root.findall(".//Tracks/*")):
        name = track.findtext(".//Name/EffectiveName", default=f"Track {i}")
        tracks.append({"index": i, "name": name})
    return tracks
