"""
Extract device information from Ableton Live XML.

Devices include:
- Instruments (InstrumentGroupDevice, PluginDevice, etc.)
- Audio effects (AudioEffectGroupDevice, Compressor, EQ, etc.)
- MIDI effects (MidiArpeggiator, MidiNoteLength, etc.)
"""

from typing import List, Dict, Any, Optional
import xml.etree.ElementTree as ET


def extract_devices(track_elem: ET.Element) -> List[Dict[str, Any]]:
    """
    Extract all devices from a track element.

    Args:
        track_elem: XML element representing a track (MidiTrack, AudioTrack, etc.)

    Returns:
        List of device dictionaries with name, type, and parameters
    """
    devices = []

    # Find the DeviceChain element
    device_chain = track_elem.find('.//DeviceChain')
    if device_chain is None:
        return devices

    # Look for different device types
    device_types = [
        ('InstrumentGroupDevice', 'instrument'),
        ('PluginDevice', 'plugin'),
        ('AuPluginDevice', 'au_plugin'),
        ('Vst3PluginDevice', 'vst3_plugin'),
        ('AudioEffectGroupDevice', 'audio_effect_group'),
        ('MidiEffectGroupDevice', 'midi_effect_group'),
        # Ableton native devices
        ('Compressor2', 'audio_effect'),
        ('Eq8', 'audio_effect'),
        ('Reverb', 'audio_effect'),
        ('Delay', 'audio_effect'),
        ('Chorus', 'audio_effect'),
        ('Saturator', 'audio_effect'),
        # MIDI effects
        ('MidiArpeggiator', 'midi_effect'),
        ('MidiNoteLength', 'midi_effect'),
        ('MidiScale', 'midi_effect'),
        ('MidiChord', 'midi_effect'),
    ]

    for device_tag, device_category in device_types:
        for device_elem in device_chain.iter(device_tag):
            device_info = _extract_device_info(device_elem, device_category)
            if device_info:
                devices.append(device_info)

    return devices


def _extract_device_info(device_elem: ET.Element, device_category: str) -> Optional[Dict[str, Any]]:
    """
    Extract information from a single device element.

    Args:
        device_elem: XML element representing a device
        device_category: Category of the device (instrument, audio_effect, etc.)

    Returns:
        Dictionary with device information
    """
    # Get device name
    name_elem = device_elem.find('.//UserName')
    if name_elem is not None and name_elem.get('Value'):
        device_name = name_elem.get('Value', '')
    else:
        # Fall back to EffectiveName or tag name
        effective_name = device_elem.find('.//EffectiveName')
        if effective_name is not None:
            device_name = effective_name.get('Value', device_elem.tag)
        else:
            device_name = device_elem.tag

    # Get device ID
    device_id = device_elem.get('Id', '')

    # Get On/Off state
    on_elem = device_elem.find('./On/Manual')
    is_enabled = on_elem.get('Value', 'true') == 'true' if on_elem is not None else True

    # Extract parameters
    parameters = _extract_parameters(device_elem)

    # For plugin devices, extract plugin info
    plugin_info = {}
    if device_category in ['plugin', 'au_plugin', 'vst3_plugin']:
        plugin_info = _extract_plugin_info(device_elem)

    device_info = {
        'name': device_name,
        'type': device_category,
        'id': device_id,
        'is_enabled': is_enabled,
        'parameters': parameters,
    }

    if plugin_info:
        device_info['plugin_info'] = plugin_info

    return device_info


def _extract_parameters(device_elem: ET.Element) -> List[Dict[str, Any]]:
    """
    Extract device parameters.

    Args:
        device_elem: XML element representing a device

    Returns:
        List of parameter dictionaries
    """
    parameters = []

    # Look for PluginFloatParameter and PluginEnumParameter
    for param_elem in device_elem.iter('PluginFloatParameter'):
        param_info = _extract_float_parameter(param_elem)
        if param_info:
            parameters.append(param_info)

    for param_elem in device_elem.iter('PluginEnumParameter'):
        param_info = _extract_enum_parameter(param_elem)
        if param_info:
            parameters.append(param_info)

    # Look for regular Manual parameters (Ableton native devices)
    for manual_elem in device_elem.iter('Manual'):
        parent = _find_parent_with_name(device_elem, manual_elem)
        if parent is not None:
            param_name = _get_element_name(parent)
            param_value = manual_elem.get('Value', '')
            if param_name and param_value:
                parameters.append({
                    'name': param_name,
                    'value': param_value,
                    'type': 'float'
                })

    return parameters


def _extract_float_parameter(param_elem: ET.Element) -> Optional[Dict[str, Any]]:
    """Extract a float parameter."""
    param_id = param_elem.get('Id', '')
    manual_elem = param_elem.find('./Manual')

    if manual_elem is not None:
        value = manual_elem.get('Value', '0')
        return {
            'id': param_id,
            'name': f'Param {param_id}',  # Plugin parameters often don't have names in XML
            'value': float(value) if value else 0.0,
            'type': 'float'
        }
    return None


def _extract_enum_parameter(param_elem: ET.Element) -> Optional[Dict[str, Any]]:
    """Extract an enum parameter."""
    param_id = param_elem.get('Id', '')
    manual_elem = param_elem.find('./Manual')

    if manual_elem is not None:
        value = manual_elem.get('Value', '0')
        return {
            'id': param_id,
            'name': f'Param {param_id}',
            'value': int(value) if value else 0,
            'type': 'enum'
        }
    return None


def _extract_plugin_info(device_elem: ET.Element) -> Dict[str, Any]:
    """
    Extract plugin-specific information (VST/AU/VST3).

    Args:
        device_elem: XML element representing a plugin device

    Returns:
        Dictionary with plugin information
    """
    plugin_info = {}

    # Find PluginDesc element
    plugin_desc = device_elem.find('.//PluginDesc')
    if plugin_desc is not None:
        # Extract VstPluginInfo or AuPluginInfo
        vst_info = plugin_desc.find('.//VstPluginInfo')
        au_info = plugin_desc.find('.//AuPluginInfo')

        if vst_info is not None:
            plugin_info['plugin_name'] = vst_info.find('./PlugName').get('Value', '') if vst_info.find('./PlugName') is not None else ''
            plugin_info['plugin_vendor'] = vst_info.find('./VendorName').get('Value', '') if vst_info.find('./VendorName') is not None else ''
        elif au_info is not None:
            plugin_info['plugin_name'] = au_info.find('./Name').get('Value', '') if au_info.find('./Name') is not None else ''
            plugin_info['plugin_manufacturer'] = au_info.find('./Manufacturer').get('Value', '') if au_info.find('./Manufacturer') is not None else ''

    return plugin_info


def _find_parent_with_name(root: ET.Element, child: ET.Element) -> Optional[ET.Element]:
    """
    Find the parent element that has a name attribute.

    This is a helper to find parameter names in the XML structure.
    """
    # This is a simplified version - in practice, you might need to traverse the tree
    # For now, return None as we'll use the structured PluginFloatParameter approach
    return None


def _get_element_name(elem: ET.Element) -> str:
    """Get the name of an element, checking various name fields."""
    # Check for Name/UserName/EffectiveName
    for name_tag in ['UserName', 'EffectiveName', 'Name']:
        name_elem = elem.find(f'.//{name_tag}')
        if name_elem is not None:
            value = name_elem.get('Value', '')
            if value:
                return value

    # Fall back to tag name
    return elem.tag
