"""
Extract clip information from Ableton Live XML.

Clips include:
- MIDI clips (notes, timing, loop settings)
- Audio clips (file references, warp settings)
"""

from typing import List, Dict, Any, Optional
import xml.etree.ElementTree as ET


def extract_clips(track_elem: ET.Element) -> List[Dict[str, Any]]:
    """
    Extract all clips from a track element.

    Args:
        track_elem: XML element representing a track (MidiTrack, AudioTrack, etc.)

    Returns:
        List of clip dictionaries with timing, name, and type information
    """
    clips = []

    # Find ClipSlotList (session view clips)
    clip_slot_list = track_elem.find('.//ClipSlotList')
    if clip_slot_list is not None:
        for clip_slot in clip_slot_list.findall('.//ClipSlot'):
            clip_info = _extract_clip_from_slot(clip_slot)
            if clip_info:
                clips.append(clip_info)

    # Find ArrangementClipList (arrangement view clips)
    arrangement_clips = track_elem.find('.//ArrangementClipList')
    if arrangement_clips is not None:
        for clip_elem in arrangement_clips:
            if clip_elem.tag in ['MidiClip', 'AudioClip']:
                clip_info = _extract_clip_info(clip_elem)
                if clip_info:
                    clip_info['view'] = 'arrangement'
                    clips.append(clip_info)

    return clips


def _extract_clip_from_slot(clip_slot: ET.Element) -> Optional[Dict[str, Any]]:
    """
    Extract clip information from a ClipSlot element.

    Args:
        clip_slot: XML element representing a clip slot

    Returns:
        Dictionary with clip information, or None if slot is empty
    """
    # Check if the slot has a clip (Value element with MidiClip or AudioClip)
    value_elem = clip_slot.find('./ClipSlot/Value')
    if value_elem is None or len(value_elem) == 0:
        return None  # Empty slot

    # Get the clip element (MidiClip or AudioClip)
    clip_elem = None
    for child in value_elem:
        if child.tag in ['MidiClip', 'AudioClip']:
            clip_elem = child
            break

    if clip_elem is None:
        return None

    clip_info = _extract_clip_info(clip_elem)
    if clip_info:
        clip_info['view'] = 'session'
        # Get slot ID
        slot_id = clip_slot.get('Id', '')
        clip_info['slot_id'] = slot_id

    return clip_info


def _extract_clip_info(clip_elem: ET.Element) -> Optional[Dict[str, Any]]:
    """
    Extract information from a MidiClip or AudioClip element.

    Args:
        clip_elem: XML element representing a clip

    Returns:
        Dictionary with clip information
    """
    clip_type = 'midi' if clip_elem.tag == 'MidiClip' else 'audio'

    # Get clip name
    name_elem = clip_elem.find('./Name')
    clip_name = ''
    if name_elem is not None:
        user_name = name_elem.find('./UserName')
        effective_name = name_elem.find('./EffectiveName')
        if user_name is not None:
            clip_name = user_name.get('Value', '')
        elif effective_name is not None:
            clip_name = effective_name.get('Value', '')

    # Get timing information
    current_start = clip_elem.find('./CurrentStart')
    current_end = clip_elem.find('./CurrentEnd')

    start_time = float(current_start.get('Value', '0')) if current_start is not None else 0.0
    end_time = float(current_end.get('Value', '0')) if current_end is not None else 0.0

    # Get loop settings
    loop_elem = clip_elem.find('./Loop')
    loop_info = {}
    if loop_elem is not None:
        loop_start_elem = loop_elem.find('./LoopStart')
        loop_end_elem = loop_elem.find('./LoopEnd')
        loop_on_elem = loop_elem.find('./LoopOn')

        loop_info = {
            'loop_start': float(loop_start_elem.get('Value', '0')) if loop_start_elem is not None else 0.0,
            'loop_end': float(loop_end_elem.get('Value', '0')) if loop_end_elem is not None else 0.0,
            'is_looped': loop_on_elem.get('Value', 'true') == 'true' if loop_on_elem is not None else True,
        }

    # Get color
    color_elem = clip_elem.find('./Color')
    color = int(color_elem.get('Value', '-1')) if color_elem is not None else -1

    clip_info = {
        'name': clip_name,
        'type': clip_type,
        'start_time': start_time,
        'end_time': end_time,
        'color': color,
        **loop_info
    }

    # Type-specific information
    if clip_type == 'midi':
        midi_info = _extract_midi_clip_info(clip_elem)
        clip_info.update(midi_info)
    elif clip_type == 'audio':
        audio_info = _extract_audio_clip_info(clip_elem)
        clip_info.update(audio_info)

    return clip_info


def _extract_midi_clip_info(clip_elem: ET.Element) -> Dict[str, Any]:
    """
    Extract MIDI-specific clip information.

    Args:
        clip_elem: XML element representing a MIDI clip

    Returns:
        Dictionary with MIDI clip information
    """
    midi_info = {}

    # Count notes (without parsing all of them for performance)
    notes_elem = clip_elem.find('.//Notes')
    if notes_elem is not None:
        key_tracks = notes_elem.findall('./KeyTracks/KeyTrack')
        total_notes = 0
        for key_track in key_tracks:
            notes = key_track.findall('./Notes/MidiNoteEvent')
            total_notes += len(notes)
        midi_info['note_count'] = total_notes

    # Get time signature
    time_signature_elem = clip_elem.find('.//TimeSignature')
    if time_signature_elem is not None:
        numerator_elem = time_signature_elem.find('./TimeSignatures/RemoteableTimeSignature/Numerator')
        denominator_elem = time_signature_elem.find('./TimeSignatures/RemoteableTimeSignature/Denominator')
        if numerator_elem is not None and denominator_elem is not None:
            midi_info['time_signature'] = f"{numerator_elem.get('Value', '4')}/{denominator_elem.get('Value', '4')}"

    # Get velocity range
    midi_info['has_notes'] = midi_info.get('note_count', 0) > 0

    return midi_info


def _extract_audio_clip_info(clip_elem: ET.Element) -> Dict[str, Any]:
    """
    Extract audio-specific clip information.

    Args:
        clip_elem: XML element representing an audio clip

    Returns:
        Dictionary with audio clip information
    """
    audio_info = {}

    # Get sample reference
    sample_ref = clip_elem.find('.//SampleRef')
    if sample_ref is not None:
        file_ref = sample_ref.find('./FileRef')
        if file_ref is not None:
            name_elem = file_ref.find('./Name')
            path_elem = file_ref.find('./Path')

            if name_elem is not None:
                audio_info['sample_name'] = name_elem.get('Value', '')
            if path_elem is not None:
                audio_info['sample_path'] = path_elem.get('Value', '')

            # Get sample hash
            hash_elem = file_ref.find('./OriginalFileSize')
            if hash_elem is not None:
                audio_info['sample_size'] = int(hash_elem.get('Value', '0'))

    # Get warp settings
    warp_mode_elem = clip_elem.find('.//WarpMode')
    if warp_mode_elem is not None:
        warp_mode_value = warp_mode_elem.get('Value', '0')
        warp_modes = {
            '0': 'Beats',
            '1': 'Tones',
            '2': 'Texture',
            '3': 'Re-Pitch',
            '4': 'Complex',
            '5': 'Complex Pro'
        }
        audio_info['warp_mode'] = warp_modes.get(warp_mode_value, 'Unknown')

    is_warped_elem = clip_elem.find('.//IsWarped')
    if is_warped_elem is not None:
        audio_info['is_warped'] = is_warped_elem.get('Value', 'true') == 'true'

    return audio_info
