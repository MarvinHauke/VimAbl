"""Extract scene information from Ableton Live XML."""


def extract_scenes(root):
    """
    Extract all scenes from the Live Set.

    Args:
        root: ElementTree root of the decompressed .als XML

    Returns:
        List of scene dicts with structure:
        {
            'index': int,
            'name': str,
            'color': int,
            'tempo': float,
            'is_tempo_enabled': bool,
            'time_signature_id': int,
            'is_time_signature_enabled': bool,
            'annotation': str
        }
    """
    scenes = []
    scene_elements = root.findall('.//Scenes/Scene')

    for index, scene_elem in enumerate(scene_elements):
        # Extract scene name
        name_elem = scene_elem.find('.//Name')
        name = name_elem.get('Value', '') if name_elem is not None else ''

        # Extract color
        color_elem = scene_elem.find('.//Color')
        color = int(color_elem.get('Value', -1)) if color_elem is not None else -1

        # Extract tempo
        tempo_elem = scene_elem.find('.//Tempo')
        tempo = float(tempo_elem.get('Value', 120.0)) if tempo_elem is not None else 120.0

        # Extract tempo enabled state
        tempo_enabled_elem = scene_elem.find('.//IsTempoEnabled')
        is_tempo_enabled = (tempo_enabled_elem.get('Value', 'false').lower() == 'true'
                           if tempo_enabled_elem is not None else False)

        # Extract time signature
        time_sig_elem = scene_elem.find('.//TimeSignatureId')
        time_signature_id = int(time_sig_elem.get('Value', 201)) if time_sig_elem is not None else 201

        # Extract time signature enabled state
        time_sig_enabled_elem = scene_elem.find('.//IsTimeSignatureEnabled')
        is_time_signature_enabled = (time_sig_enabled_elem.get('Value', 'false').lower() == 'true'
                                     if time_sig_enabled_elem is not None else False)

        # Extract annotation
        annotation_elem = scene_elem.find('.//Annotation')
        annotation = annotation_elem.get('Value', '') if annotation_elem is not None else ''

        scene_data = {
            'index': index,
            'name': name,
            'color': color,
            'tempo': tempo,
            'is_tempo_enabled': is_tempo_enabled,
            'time_signature_id': time_signature_id,
            'is_time_signature_enabled': is_time_signature_enabled,
            'annotation': annotation
        }

        scenes.append(scene_data)

    return scenes
