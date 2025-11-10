import gzip
import xml.etree.ElementTree as ET
from pathlib import Path


def load_ableton_xml(path: Path) -> ET.ElementTree:
    """Load and parse Ableton .als or .xml file into an ElementTree."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if path.suffix == ".als":
        with gzip.open(path, "rb") as f:
            xml_data = f.read().decode("utf-8")
        return ET.ElementTree(ET.fromstring(xml_data))
    elif path.suffix == ".xml":
        return ET.parse(path)
    else:
        raise ValueError(f"Unsupported file type: {path.suffix}")
