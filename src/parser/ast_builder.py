from .file_refs import extract_file_refs
from .tracks import extract_tracks


def build_ast(root):
    return {
        "tracks": extract_tracks(root),
        "file_refs": extract_file_refs(root),
    }
