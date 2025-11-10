import xml.etree.ElementTree as ET


def extract_file_refs(root: ET.Element):
    """Extract file references, names, paths, and hashes."""
    refs = []
    for fileref in root.findall(".//FileRef"):
        ref_type = fileref.get("Type") or "Unknown"
        hash_tag = fileref.find(".//Hash")
        hash_val = hash_tag.get("Value") if hash_tag is not None else None

        name = None
        path = None
        for tag in ["Name", "OriginalFileName", "RelativePath", "Path"]:
            elem = fileref.find(f".//{tag}[@Value]")
            if elem is not None:
                if tag in ("Path", "RelativePath"):
                    path = elem.get("Value")
                else:
                    name = elem.get("Value")

        refs.append(
            {
                "type": ref_type,
                "name": name,
                "path": path,
                "hash": hash_val,
            }
        )
    return refs
